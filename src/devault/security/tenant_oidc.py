from __future__ import annotations

import logging
import secrets
import uuid
from typing import Any, Literal

import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from devault.db.models import ConsoleUser, Tenant, TenantMembership
from devault.security.auth_context import AuthContext, RoleName
from devault.security.oidc import _jwks_client, fetch_jwks_uri_for_issuer
from devault.security.passwords import hash_password

logger = logging.getLogger(__name__)

MembershipRole = Literal["tenant_admin", "operator", "auditor"]


def _map_claim_to_auth_role(raw: str) -> RoleName | None:
    r = raw.strip().lower()
    if r in ("tenant_admin", "admin"):
        return "admin"
    if r == "operator":
        return "operator"
    if r == "auditor":
        return "auditor"
    return None


def _auth_to_membership_role(role: RoleName) -> MembershipRole:
    if role == "admin":
        return "tenant_admin"
    if role == "operator":
        return "operator"
    return "auditor"


def _normalize_email_claim(claims: dict[str, Any], claim_name: str) -> str | None:
    v = claims.get(claim_name)
    if isinstance(v, str):
        s = v.strip().lower()
        if "@" in s and "." in s.split("@")[-1]:
            return s
    return None


def _jit_upsert_membership(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    email: str,
    membership_role: MembershipRole,
) -> bool:
    """Create or update membership; returns True if DB state may need commit."""
    user = db.scalar(select(ConsoleUser).where(ConsoleUser.email == email))
    if user is None:
        user = ConsoleUser(
            email=email,
            password_hash=hash_password(secrets.token_urlsafe(48)),
            disabled=False,
        )
        db.add(user)
        db.flush()
    row = db.scalar(
        select(TenantMembership).where(
            TenantMembership.user_id == user.id,
            TenantMembership.tenant_id == tenant_id,
        )
    )
    if row is None:
        db.add(TenantMembership(user_id=user.id, tenant_id=tenant_id, role=membership_role))
        return True
    if row.role != membership_role:
        row.role = membership_role
        return True
    return False


def try_decode_tenant_oidc_bearer(db: Session, raw_token: str) -> AuthContext | None:
    """Validate JWT against a tenant's OIDC issuer+audience; optional JIT membership (§十六-12)."""
    parts = raw_token.split(".")
    if len(parts) != 3:
        return None
    try:
        unverified: dict[str, Any] = jwt.decode(
            raw_token,
            options={
                "verify_signature": False,
                "verify_aud": False,
                "verify_exp": False,
                "verify_iss": False,
            },
        )
    except Exception:
        return None
    iss_raw = unverified.get("iss")
    aud_raw = unverified.get("aud")
    if not isinstance(iss_raw, str) or not isinstance(aud_raw, str):
        return None
    issuer = iss_raw.strip().rstrip("/")
    audience = aud_raw.strip()
    if not issuer or not audience:
        return None

    tenant = db.scalar(
        select(Tenant).where(
            Tenant.sso_oidc_issuer == issuer,
            Tenant.sso_oidc_audience == audience,
        )
    )
    if tenant is None:
        return None

    jwks_uri = fetch_jwks_uri_for_issuer(issuer)
    if not jwks_uri:
        return None
    try:
        signing_key = _jwks_client(jwks_uri).get_signing_key_from_jwt(raw_token)
        claims = jwt.decode(
            raw_token,
            signing_key.key,
            algorithms=["RS256", "ES256", "EdDSA"],
            audience=audience,
            issuer=issuer,
            options={"require": ["exp", "iat"]},
        )
    except Exception as e:
        logger.debug("tenant OIDC verify failed tenant_id=%s: %s", tenant.id, e)
        return None

    role_raw = claims.get(tenant.sso_oidc_role_claim) or claims.get("devault_role")
    if isinstance(role_raw, list) and role_raw:
        role_raw = role_raw[0]
    if not isinstance(role_raw, str):
        return None
    role = _map_claim_to_auth_role(role_raw)
    if role is None:
        logger.warning("tenant OIDC unsupported role %r tenant_id=%s", role_raw, tenant.id)
        return None

    email = _normalize_email_claim(claims, tenant.sso_oidc_email_claim) or _normalize_email_claim(
        claims,
        "email",
    )

    if tenant.sso_jit_provisioning and email:
        try:
            if _jit_upsert_membership(
                db,
                tenant_id=tenant.id,
                email=email,
                membership_role=_auth_to_membership_role(role),
            ):
                db.commit()
        except Exception:
            logger.exception("tenant OIDC JIT provisioning failed tenant_id=%s", tenant.id)
            db.rollback()
            return None

    sub = str(claims.get("sub") or "unknown")
    label = f"oidc-tenant:{tenant.slug}:{sub}"
    return AuthContext(
        role=role,
        allowed_tenant_ids=frozenset({tenant.id}),
        principal_label=label,
    )
