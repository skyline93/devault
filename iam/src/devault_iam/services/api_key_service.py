from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from devault_iam.db.models import ApiKey, ApiKeyScope, Permission
from devault_iam.security.jwt_tokens import AccessTokenClaims, issue_access_token
from devault_iam.settings import Settings


def _hash_secret(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def validate_scope_keys(db: Session, keys: list[str]) -> None:
    keys = [k.strip() for k in keys if k.strip()]
    if not keys:
        raise ValueError("scopes_required")
    for k in keys:
        exists = db.scalar(select(Permission.id).where(Permission.key == k))
        if exists is None:
            raise ValueError(f"unknown_permission:{k}")


def create_api_key(
    db: Session,
    *,
    tenant_id: uuid.UUID | None,
    name: str,
    scope_keys: list[str],
    created_by_user_id: uuid.UUID,
    expires_at: datetime | None,
) -> tuple[ApiKey, str]:
    validate_scope_keys(db, scope_keys)
    kid = uuid.uuid4()
    secret_part = secrets.token_urlsafe(32)
    full_secret = f"dvk.{kid}.{secret_part}"
    h = _hash_secret(full_secret)
    prefix = f"dvk.{str(kid)[:8]}"
    row = ApiKey(
        id=kid,
        tenant_id=tenant_id,
        name=name.strip(),
        key_prefix=prefix,
        key_hash=h,
        created_by_user_id=created_by_user_id,
        expires_at=expires_at,
        enabled=True,
    )
    db.add(row)
    db.flush()
    for k in sorted({s.strip() for s in scope_keys if s.strip()}):
        db.add(ApiKeyScope(api_key_id=row.id, permission_key=k))
    db.commit()
    db.refresh(row)
    return row, full_secret


def parse_api_key_id_from_secret(raw: str) -> uuid.UUID:
    parts = raw.strip().split(".")
    if len(parts) != 3 or parts[0] != "dvk":
        raise ValueError("invalid_api_key_format")
    return uuid.UUID(parts[1])


def verify_api_key_secret(db: Session, raw: str) -> ApiKey | None:
    try:
        kid = parse_api_key_id_from_secret(raw)
    except ValueError:
        return None
    h = _hash_secret(raw.strip())
    row = db.scalar(select(ApiKey).where(ApiKey.id == kid, ApiKey.key_hash == h))
    if row is None or not row.enabled:
        return None
    if row.expires_at is not None:
        exp = row.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < _utcnow():
            return None
    return row


def issue_access_token_for_api_key(
    db: Session,
    *,
    private_key_pem: str,
    settings: Settings,
    key_row: ApiKey,
) -> str:
    rows = db.scalars(select(ApiKeyScope.permission_key).where(ApiKeyScope.api_key_id == key_row.id)).all()
    scopes = sorted({str(x) for x in rows})
    tid = key_row.tenant_id
    tids: list[uuid.UUID] = [tid] if tid is not None else []
    claims = AccessTokenClaims(
        sub=f"api_key:{key_row.id}",
        tid=tid,
        tids=tids,
        perm=scopes,
        pk="api_key",
        mfa=True,
        email="",
        name="",
    )
    return issue_access_token(
        private_key_pem=private_key_pem,
        settings=settings,
        claims=claims,
        ttl_seconds=settings.api_key_access_token_ttl_seconds,
    )


def set_api_key_enabled(db: Session, key_id: uuid.UUID, enabled: bool) -> ApiKey | None:
    row = db.get(ApiKey, key_id)
    if row is None:
        return None
    row.enabled = enabled
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete_api_key(db: Session, key_id: uuid.UUID) -> bool:
    row = db.get(ApiKey, key_id)
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True
