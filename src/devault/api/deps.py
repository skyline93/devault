from __future__ import annotations

import uuid
from collections.abc import Generator

from fastapi import Cookie, Depends, Header, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import select
from sqlalchemy.orm import Session

from devault.db.models import Tenant
from devault.db.session import SessionLocal
from devault.security.auth_context import AuthContext, dev_open_auth_context
from devault.security.oidc import try_decode_oidc_bearer
from devault.security.policy import authentication_enabled
from devault.security.token_resolve import resolve_bearer_token
from devault.settings import Settings, get_settings

_ui_security = HTTPBasic(auto_error=False)

UI_TENANT_COOKIE = "devault_ui_tenant"


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_ui_basic_auth(
    credentials: HTTPBasicCredentials | None = Depends(_ui_security),
    db: Session = Depends(get_db),
) -> AuthContext:
    settings = get_settings()
    if not authentication_enabled(settings, db):
        return dev_open_auth_context()
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": 'Basic realm="DeVault UI"'},
        )
    raw = (credentials.password or "").strip()
    if not raw:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    ctx = try_decode_oidc_bearer(raw, settings)
    if ctx is not None:
        return ctx
    try:
        return resolve_bearer_token(db, raw, legacy_api_token=settings.api_token)
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials") from None


def get_auth_context(
    authorization: str | None = Header(None),
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
    ctx = try_decode_oidc_bearer(raw, settings)
    if ctx is not None:
        return ctx
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


def require_write_ui(auth: AuthContext = Depends(verify_ui_basic_auth)) -> AuthContext:
    auth.ensure_can_write()
    return auth


def require_admin_ui(auth: AuthContext = Depends(verify_ui_basic_auth)) -> AuthContext:
    auth.ensure_admin()
    return auth


def _resolve_tenant_by_uuid_pref(
    db: Session,
    raw: str,
) -> Tenant:
    """Resolve tenant UUID from header / UI cookie preference string."""
    s = raw.strip()
    if not s:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="empty tenant id")
    try:
        tid = uuid.UUID(s)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid tenant id",
        ) from e
    t = db.get(Tenant, tid)
    if t is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant not found")
    return t


def tenants_for_switcher_nav(db: Session, auth: AuthContext) -> list[Tenant]:
    """Tenants visible in Web UI tenant switch (ordered by slug)."""
    stmt = select(Tenant).order_by(Tenant.slug.asc())
    rows = list(db.scalars(stmt).all())
    if auth.allowed_tenant_ids is None:
        return rows
    allow = auth.allowed_tenant_ids
    return [x for x in rows if x.id in allow]


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


def get_effective_tenant_ui(
    db: Session = Depends(get_db),
    devault_ui_tenant: str | None = Cookie(None, alias=UI_TENANT_COOKIE),
    x_devault_tenant_id: str | None = Header(None, alias="X-DeVault-Tenant-Id"),
    auth: AuthContext = Depends(verify_ui_basic_auth),
) -> Tenant:
    """Effective tenant for `/ui/*`: **Cookie preferred**, then **`X-DeVault-Tenant-Id`**, else default slug."""
    settings = get_settings()
    cookie_hint = (devault_ui_tenant or "").strip()
    header_hint = (x_devault_tenant_id or "").strip()

    pref: str | None = None
    if cookie_hint:
        pref = devault_ui_tenant
    elif x_devault_tenant_id is not None and header_hint != "":
        pref = x_devault_tenant_id

    if pref is not None and pref.strip():
        t = _resolve_tenant_by_uuid_pref(db, pref)
        auth.ensure_tenant_access(t.id)
        return t
    t = _resolve_tenant_row(db, x_devault_tenant_id=None, settings=settings)
    auth.ensure_tenant_access(t.id)
    return t
