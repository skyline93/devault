from __future__ import annotations

import uuid
from collections.abc import Generator
from dataclasses import replace

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from devault.db.models import Tenant
from devault.db.session import SessionLocal
from devault.security.auth_context import AuthContext, dev_open_auth_context
from devault.security.console_session_auth import (
    console_user_auth_context,
    load_user_for_session,
    resolve_effective_tenant_id_for_console_user,
)
from devault.security.http_session_store import load_session
from devault.security.oidc import try_decode_oidc_bearer
from devault.security.tenant_oidc import try_decode_tenant_oidc_bearer
from devault.security.policy import authentication_enabled
from devault.security.token_resolve import resolve_bearer_token
from devault.settings import Settings, get_settings


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_auth_context(
    request: Request,
    authorization: str | None = Header(None),
    x_devault_tenant_id: str | None = Header(None, alias="X-DeVault-Tenant-Id"),
    db: Session = Depends(get_db),
) -> AuthContext:
    settings = get_settings()
    if not authentication_enabled(settings, db):
        return dev_open_auth_context()

    sid = request.cookies.get(settings.session_cookie_name)
    if sid:
        payload = load_session(settings.redis_url, sid)
        if payload is not None:
            user = load_user_for_session(db, payload.user_id)
            if user is None:
                pass
            elif user.disabled:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="session user disabled",
                )
            else:
                try:
                    tid = resolve_effective_tenant_id_for_console_user(
                        db,
                        settings,
                        x_devault_tenant_id=x_devault_tenant_id,
                        user_id=user.id,
                    )
                    ctx = console_user_auth_context(
                        db,
                        settings,
                        user=user,
                        effective_tenant_id=tid,
                    )
                    return replace(ctx, mfa_satisfied=payload.mfa_verified)
                except PermissionError as e:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=str(e) or "session not valid for this principal",
                    ) from e

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
    ctx = try_decode_oidc_bearer(raw, settings)
    if ctx is not None:
        return ctx
    ctx_t = try_decode_tenant_oidc_bearer(db, raw)
    if ctx_t is not None:
        return ctx_t
    try:
        return resolve_bearer_token(db, raw, legacy_api_token=settings.api_token)
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid bearer token",
        ) from e


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
    settings: Settings,
) -> Tenant:
    if x_devault_tenant_id is not None:
        raw = x_devault_tenant_id.strip()
        if not raw:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="empty X-DeVault-Tenant-Id")
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
    t = db.scalar(select(Tenant).where(Tenant.slug == settings.default_tenant_slug))
    if t is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"no tenant with slug {settings.default_tenant_slug!r}; run migrations",
        )
    return t


def get_effective_tenant(
    db: Session = Depends(get_db),
    x_devault_tenant_id: str | None = Header(None, alias="X-DeVault-Tenant-Id"),
    auth: AuthContext = Depends(get_auth_context),
) -> Tenant:
    settings = get_settings()
    t = _resolve_tenant_row(db, x_devault_tenant_id=x_devault_tenant_id, settings=settings)
    auth.ensure_tenant_access(t.id)
    return t
