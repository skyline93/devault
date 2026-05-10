from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from devault_iam.api.deps import get_db
from devault_iam.api.principal import get_jwt_pem, parse_optional_tenant_header
from devault_iam.db.models import ApiKeyScope, User
from devault_iam.schemas.auth import LoginIn, LogoutIn, RefreshIn, RegisterIn, TokenOut
from devault_iam.schemas.p2 import ApiKeyGrantIn, ApiKeyTokenOut
from devault_iam.security.rate_limit import check_sliding_login_rate_limit, check_sliding_rate_limit
from devault_iam.services import api_key_service
from devault_iam.services import auth_service
from devault_iam.services import permissions as perm_svc
from devault_iam.services.audit_service import mask_email, record_audit_event
from devault_iam.services.auth_service import issue_access_for_user, login_user, refresh_session, register_user
from devault_iam.settings import Settings, get_settings

router = APIRouter(prefix="/v1/auth", tags=["auth"])


def _client_ip(request: Request) -> str | None:
    if request.client:
        return request.client.host
    return None


def _audit_req(request: Request) -> dict:
    return {
        "request_id": getattr(request.state, "request_id", None),
        "ip": _client_ip(request),
        "user_agent": request.headers.get("user-agent"),
    }


def _lookup_user_id_by_email(db: Session, email: str) -> uuid.UUID | None:
    return db.scalar(select(User.id).where(User.email == email.strip().lower()))


def _issue_token_bundle(
    request: Request,
    db: Session,
    settings: Settings,
    *,
    user: User,
    effective_tid: uuid.UUID,
    refresh_raw: str,
) -> TokenOut:
    priv, _pub = get_jwt_pem(request)
    access = issue_access_for_user(
        db,
        private_key_pem=priv,
        settings=settings,
        user=user,
        effective_tenant_id=effective_tid,
    )
    perms = perm_svc.union_permission_keys_for_user(db, user.id)
    return TokenOut(
        access_token=access,
        refresh_token=refresh_raw,
        expires_in=settings.access_token_ttl_seconds,
        tenant_id=effective_tid,
        permissions=perms,
    )


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def post_register(
    request: Request,
    body: RegisterIn,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    x_devault_tenant_id: str | None = Header(default=None, alias="X-DeVault-Tenant-Id"),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
) -> TokenOut:
    try:
        register_user(
            db,
            settings,
            email=str(body.email),
            password=body.password,
            name=body.name,
        )
    except ValueError as e:
        code = str(e)
        record_audit_event(
            action="auth.register",
            outcome="failure",
            detail=code,
            context={"email_masked": mask_email(str(body.email))},
            **_audit_req(request),
        )
        if code == "email_taken":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email_taken") from e
        if code == "registration_disabled":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="registration_disabled") from e
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=code) from e

    hdr_tid = parse_optional_tenant_header(x_devault_tenant_id, x_tenant_id)
    try:
        u2, refresh = login_user(
            db,
            settings,
            email=str(body.email),
            password=body.password,
            mfa_code=None,
            tenant_id=hdr_tid,
            client_ip=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="login_after_register_failed",
        )
    tid = perm_svc.resolve_effective_tenant_id(db, u2.id, requested_tenant_id=hdr_tid)
    record_audit_event(
        action="auth.register",
        outcome="success",
        actor_user_id=u2.id,
        tenant_id=tid,
        **_audit_req(request),
    )
    return _issue_token_bundle(request, db, settings, user=u2, effective_tid=tid, refresh_raw=refresh)


@router.post("/login", response_model=TokenOut)
def post_login(
    request: Request,
    body: LoginIn,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    x_devault_tenant_id: str | None = Header(default=None, alias="X-DeVault-Tenant-Id"),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
) -> TokenOut:
    ip = _client_ip(request) or "unknown"
    try:
        check_sliding_login_rate_limit(
            settings.redis_url,
            ip,
            max_per_minute=settings.login_rate_limit_per_minute,
        )
    except PermissionError:
        record_audit_event(
            action="auth.login",
            outcome="failure",
            detail="rate_limited",
            context={"email_masked": mask_email(str(body.email))},
            **_audit_req(request),
        )
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="rate_limited") from None

    hdr_tid = parse_optional_tenant_header(x_devault_tenant_id, x_tenant_id)
    requested = body.tenant_id or hdr_tid

    try:
        user, refresh = login_user(
            db,
            settings,
            email=str(body.email),
            password=body.password,
            mfa_code=body.mfa_code,
            tenant_id=requested,
            client_ip=ip,
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as e:
        code = str(e)
        actor_try = _lookup_user_id_by_email(db, str(body.email))
        record_audit_event(
            action="auth.login",
            outcome="failure",
            actor_user_id=actor_try,
            detail=code,
            context={"email_masked": mask_email(str(body.email))},
            **_audit_req(request),
        )
        if code == "mfa_required":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "mfa_required", "message": "MFA code required"},
            ) from e
        if code == "mfa_invalid":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="mfa_invalid") from e
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials") from e

    tid = perm_svc.resolve_effective_tenant_id(db, user.id, requested_tenant_id=requested)
    record_audit_event(
        action="auth.login",
        outcome="success",
        actor_user_id=user.id,
        tenant_id=tid,
        **_audit_req(request),
    )
    return _issue_token_bundle(request, db, settings, user=user, effective_tid=tid, refresh_raw=refresh)


@router.post("/refresh", response_model=TokenOut)
def post_refresh(
    request: Request,
    body: RefreshIn,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    x_devault_tenant_id: str | None = Header(default=None, alias="X-DeVault-Tenant-Id"),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
) -> TokenOut:
    hdr_tid = parse_optional_tenant_header(x_devault_tenant_id, x_tenant_id)
    requested = body.tenant_id or hdr_tid
    try:
        result = refresh_session(
            db,
            settings,
            raw_refresh=body.refresh_token,
            tenant_id=requested,
            client_ip=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError:
        record_audit_event(
            action="auth.refresh",
            outcome="failure",
            detail="invalid_refresh",
            **_audit_req(request),
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_refresh") from None

    record_audit_event(
        action="auth.refresh",
        outcome="success",
        actor_user_id=result.user.id,
        tenant_id=result.effective_tenant_id,
        **_audit_req(request),
    )
    return _issue_token_bundle(
        request,
        db,
        settings,
        user=result.user,
        effective_tid=result.effective_tenant_id,
        refresh_raw=result.refresh_token,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def post_logout(
    body: LogoutIn,
    db: Session = Depends(get_db),
) -> None:
    auth_service.revoke_refresh_token(db, body.refresh_token)


@router.post("/token", response_model=ApiKeyTokenOut)
def post_api_key_token(
    request: Request,
    body: ApiKeyGrantIn,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ApiKeyTokenOut:
    if body.grant_type != "api_key":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unsupported_grant_type")
    ip = _client_ip(request) or "unknown"
    try:
        check_sliding_rate_limit(
            settings.redis_url,
            ip,
            max_per_minute=settings.login_rate_limit_per_minute,
            key_prefix="devault_iam:api_key_token_rl",
        )
    except PermissionError:
        record_audit_event(
            action="auth.api_key_token",
            outcome="failure",
            detail="rate_limited",
            **_audit_req(request),
        )
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="rate_limited") from None

    row = api_key_service.verify_api_key_secret(db, body.api_key)
    if row is None:
        record_audit_event(
            action="auth.api_key_token",
            outcome="failure",
            detail="invalid_api_key",
            **_audit_req(request),
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_api_key")
    priv, _pub = get_jwt_pem(request)
    access = api_key_service.issue_access_token_for_api_key(
        db,
        private_key_pem=priv,
        settings=settings,
        key_row=row,
    )
    scopes = sorted(
        str(x)
        for x in db.scalars(
            select(ApiKeyScope.permission_key).where(ApiKeyScope.api_key_id == row.id)
        ).all()
    )
    record_audit_event(
        action="auth.api_key_token",
        outcome="success",
        tenant_id=row.tenant_id,
        resource_type="api_key",
        resource_id=str(row.id),
        **_audit_req(request),
    )
    return ApiKeyTokenOut(
        access_token=access,
        expires_in=settings.api_key_access_token_ttl_seconds,
        tenant_id=row.tenant_id,
        permissions=scopes,
    )
