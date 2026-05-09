from __future__ import annotations

import hashlib
import secrets
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from devault.db.models import ControlPlaneApiKey
from devault.security.auth_context import AuthContext, RoleName, legacy_token_context


def hash_api_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _row_to_context(row: ControlPlaneApiKey) -> AuthContext:
    role: RoleName
    if row.role not in ("admin", "operator", "auditor"):
        role = "operator"
    else:
        role = row.role  # type: ignore[assignment]
    raw = row.allowed_tenant_ids
    if raw is None:
        allowed: frozenset[uuid.UUID] | None = None
    elif not isinstance(raw, list):
        allowed = frozenset()
    else:
        allowed = frozenset(uuid.UUID(str(x)) for x in raw)
    return AuthContext(role=role, allowed_tenant_ids=allowed, principal_label=row.name)


def resolve_bearer_token(db: Session | None, raw_token: str, *, legacy_api_token: str | None) -> AuthContext:
    """Resolve Bearer secret: DB API keys, else legacy DEVAULT_API_TOKEN (timing-safe)."""
    if not raw_token:
        raise ValueError("empty token")

    h = hash_api_token(raw_token)
    if db is not None:
        row = db.scalar(
            select(ControlPlaneApiKey).where(
                ControlPlaneApiKey.token_hash == h,
                ControlPlaneApiKey.enabled.is_(True),
            )
        )
        if row is not None:
            return _row_to_context(row)

    if legacy_api_token and secrets.compare_digest(raw_token, legacy_api_token):
        return legacy_token_context()

    raise PermissionError("invalid bearer token")
