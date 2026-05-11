from __future__ import annotations

import uuid
from collections.abc import Generator

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from devault.db.models import Tenant
from devault.db.session import SessionLocal
from devault.security.auth_context import AuthContext, dev_open_auth_context
from devault.security.iam_jwt import try_decode_iam_bearer
from devault.security.policy import authentication_enabled
from devault.settings import get_settings


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_auth_context(
    authorization: str | None = Header(None),
    x_devault_tenant_id: str | None = Header(None, alias="X-DeVault-Tenant-Id"),
    db: Session = Depends(get_db),
) -> AuthContext:
    settings = get_settings()
    if not authentication_enabled(settings, db):
        return dev_open_auth_context()

    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )
    raw = authorization.removeprefix("Bearer ").strip()
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )
    ctx = try_decode_iam_bearer(raw, settings)
    if ctx is not None:
        return ctx
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired IAM access token",
    )


def require_write(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
    auth.ensure_can_write()
    return auth


def require_admin(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
    auth.ensure_admin()
    return auth


def ensure_platform_or_tenant_admin_for_tenant(
    auth: AuthContext,
    tenant_id: uuid.UUID,
) -> None:
    """PATCH tenant / legal-hold style: scoped platform admin or tenant_admin for that tenant."""
    if auth.principal_kind == "tenant_user":
        if auth.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="tenant administrator role required",
            )
        auth.ensure_tenant_access(tenant_id)
        return
    auth.ensure_admin()
    if auth.allowed_tenant_ids is not None and tenant_id not in auth.allowed_tenant_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="tenant not in token scope",
        )


def _resolve_tenant_row(
    db: Session,
    *,
    x_devault_tenant_id: str | None,
) -> Tenant:
    """Resolve tenant **only** from ``X-DeVault-Tenant-Id`` (no slug / default fallback)."""
    if x_devault_tenant_id is None or not str(x_devault_tenant_id).strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-DeVault-Tenant-Id header is required",
        )
    raw = x_devault_tenant_id.strip()
    try:
        tid = uuid.UUID(raw)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid X-DeVault-Tenant-Id",
        ) from e
    t = db.get(Tenant, tid)
    if t is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant not found")
    return t


def get_effective_tenant(
    db: Session = Depends(get_db),
    x_devault_tenant_id: str | None = Header(None, alias="X-DeVault-Tenant-Id"),
    auth: AuthContext = Depends(get_auth_context),
) -> Tenant:
    t = _resolve_tenant_row(db, x_devault_tenant_id=x_devault_tenant_id)
    auth.ensure_tenant_access(t.id)
    return t
