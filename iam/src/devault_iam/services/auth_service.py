from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pyotp
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from devault_iam.db.models import Session as UserSession
from devault_iam.db.models import TenantMember, User
from devault_iam.security.jwt_tokens import AccessTokenClaims, issue_access_token
from devault_iam.security.passwords import hash_password, verify_password
from devault_iam.services import permissions as perm_svc
from devault_iam.settings import Settings


def _refresh_hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def count_users(db: Session) -> int:
    return int(db.scalar(select(func.count()).select_from(User)) or 0)


def register_user(
    db: Session,
    settings: Settings,
    *,
    email: str,
    password: str,
    name: str | None,
) -> User:
    email_n = email.strip().lower()
    if db.scalar(select(User.id).where(User.email == email_n)) is not None:
        raise ValueError("email_taken")
    n_users = count_users(db)
    if not settings.self_registration_enabled and n_users > 0:
        raise ValueError("registration_disabled")

    role_name = "platform_admin" if n_users == 0 else "operator"
    role = perm_svc.get_template_role(db, role_name)
    if role is None:
        raise RuntimeError("rbac_seed_missing")
    default_tenant = perm_svc.get_default_tenant(db)
    if default_tenant is None:
        raise RuntimeError("default_tenant_missing")

    user = User(
        email=email_n,
        password_hash=hash_password(password),
        name=(name or "").strip() or email_n.split("@")[0],
        status="active",
    )
    db.add(user)
    db.flush()
    db.add(
        TenantMember(
            tenant_id=default_tenant.id,
            user_id=user.id,
            role_id=role.id,
            status="active",
        )
    )
    if n_users == 0 and default_tenant.owner_user_id is None:
        default_tenant.owner_user_id = user.id
    db.commit()
    db.refresh(user)
    return user


def _mfa_satisfied(user: User, mfa_code: str | None) -> bool:
    if not user.mfa_enabled or user.totp_secret is None or user.totp_confirmed_at is None:
        return True
    if not (mfa_code or "").strip():
        return False
    return bool(pyotp.TOTP(user.totp_secret).verify(mfa_code.strip(), valid_window=1))


def login_user(
    db: Session,
    settings: Settings,
    *,
    email: str,
    password: str,
    mfa_code: str | None,
    tenant_id: uuid.UUID | None,
    client_ip: str | None,
    user_agent: str | None,
) -> tuple[User, str]:
    email_n = email.strip().lower()
    user = db.scalar(select(User).where(User.email == email_n))
    if user is None or not verify_password(user.password_hash, password):
        raise ValueError("invalid_credentials")
    if user.status != "active":
        raise ValueError("invalid_credentials")
    if not _mfa_satisfied(user, mfa_code):
        raise ValueError("mfa_required" if not (mfa_code or "").strip() else "mfa_invalid")

    tid = perm_svc.resolve_effective_tenant_id(db, user.id, requested_tenant_id=tenant_id)

    raw_refresh = secrets.token_urlsafe(48)
    h = _refresh_hash(raw_refresh)
    exp = _utcnow() + timedelta(seconds=settings.refresh_token_ttl_seconds)
    db.add(
        UserSession(
            user_id=user.id,
            refresh_token_hash=h,
            ip=client_ip,
            user_agent=user_agent,
            expires_at=exp,
        )
    )
    db.commit()
    db.refresh(user)
    return user, raw_refresh


def revoke_refresh_token(db: Session, raw_refresh: str) -> int:
    h = _refresh_hash(raw_refresh.strip())
    row = db.scalar(select(UserSession).where(UserSession.refresh_token_hash == h))
    if row is None:
        return 0
    db.delete(row)
    db.commit()
    return 1


@dataclass(frozen=True, slots=True)
class RefreshResult:
    user: User
    refresh_token: str
    effective_tenant_id: uuid.UUID


def refresh_session(
    db: Session,
    settings: Settings,
    *,
    raw_refresh: str,
    tenant_id: uuid.UUID | None,
    client_ip: str | None,
    user_agent: str | None,
) -> RefreshResult:
    h = _refresh_hash(raw_refresh.strip())
    row = db.scalar(select(UserSession).where(UserSession.refresh_token_hash == h))
    if row is None:
        raise ValueError("invalid_refresh")
    if row.expires_at < _utcnow():
        db.delete(row)
        db.commit()
        raise ValueError("invalid_refresh")
    user = db.get(User, row.user_id)
    if user is None or user.status != "active":
        db.delete(row)
        db.commit()
        raise ValueError("invalid_refresh")

    effective_tid = perm_svc.resolve_effective_tenant_id(db, user.id, requested_tenant_id=tenant_id)

    db.delete(row)
    db.flush()

    new_raw = secrets.token_urlsafe(48)
    new_h = _refresh_hash(new_raw)
    exp = _utcnow() + timedelta(seconds=settings.refresh_token_ttl_seconds)
    db.add(
        UserSession(
            user_id=user.id,
            refresh_token_hash=new_h,
            ip=client_ip,
            user_agent=user_agent,
            expires_at=exp,
        )
    )
    db.commit()
    db.refresh(user)
    return RefreshResult(user=user, refresh_token=new_raw, effective_tenant_id=effective_tid)


def build_access_claims(db: Session, user: User, effective_tenant_id: uuid.UUID) -> AccessTokenClaims:
    tids = perm_svc.tenant_ids_for_user(db, user.id)
    perms = perm_svc.union_permission_keys_for_user(db, user.id)
    pk = perm_svc.principal_kind_for_user(db, user.id)
    mfa_ok = (not user.mfa_enabled) or (user.totp_confirmed_at is not None)
    return AccessTokenClaims(
        sub=str(user.id),
        tid=effective_tenant_id,
        tids=tids,
        perm=perms,
        pk=pk,
        mfa=mfa_ok,
    )


def issue_access_for_user(
    db: Session,
    *,
    private_key_pem: str,
    settings: Settings,
    user: User,
    effective_tenant_id: uuid.UUID,
) -> str:
    claims = build_access_claims(db, user, effective_tenant_id)
    return issue_access_token(
        private_key_pem=private_key_pem,
        settings=settings,
        claims=claims,
        ttl_seconds=settings.access_token_ttl_seconds,
    )


def start_mfa_enrollment(user: User) -> tuple[str, str]:
    """Return (base32_secret, otpauth_uri). Does not persist until confirm."""
    if user.mfa_enabled and user.totp_confirmed_at is not None:
        raise ValueError("mfa_already_enabled")
    secret = pyotp.random_base32()
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name=user.email, issuer_name="DeVault-IAM")
    return secret, uri


def confirm_mfa_enrollment(db: Session, user: User, secret: str, code: str) -> None:
    if not pyotp.TOTP(secret).verify(code.strip(), valid_window=1):
        raise ValueError("mfa_invalid")
    user.totp_secret = secret
    user.totp_confirmed_at = _utcnow()
    user.mfa_enabled = True
    db.add(user)
    db.commit()


def disable_mfa(db: Session, user: User, password: str, code: str) -> None:
    if not verify_password(user.password_hash, password):
        raise ValueError("invalid_password")
    if user.totp_secret is None:
        raise ValueError("mfa_not_enabled")
    if not pyotp.TOTP(user.totp_secret).verify(code.strip(), valid_window=1):
        raise ValueError("mfa_invalid")
    user.mfa_enabled = False
    user.totp_secret = None
    user.totp_confirmed_at = None
    db.add(user)
    db.commit()
