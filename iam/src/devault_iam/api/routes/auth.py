from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from devault_iam.api.deps import get_db
from devault_iam.api.principal import Principal, get_current_principal, get_jwt_pem, parse_optional_tenant_header
from devault_iam.db.models import ApiKeyScope, User
from devault_iam.schemas.auth import ChangePasswordIn, LoginIn, LogoutIn, RefreshIn, TokenOut
from devault_iam.schemas.p2 import ApiKeyGrantIn, ApiKeyTokenOut
from devault_iam.security.rate_limit import check_sliding_login_rate_limit, check_sliding_rate_limit
from devault_iam.services import api_key_service
from devault_iam.services import auth_service
from devault_iam.services import permissions as perm_svc
from devault_iam.services.audit_service import mask_email, record_audit_event
from devault_iam.security.passwords import assert_password_policy, hash_password, verify_password
from devault_iam.services.auth_service import issue_access_for_user, login_user, refresh_session
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
    effective_tid: uuid.UUID | None,
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
        must_change_password=bool(user.must_change_password),
    )


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
        user, refresh, eff_tid = login_user(
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
        if code == "platform_user_tenant_disallowed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="platform_user_tenant_disallowed",
            ) from e
        if code in ("tenant not allowed for user", "user has no tenant memberships"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="tenant_not_allowed") from e
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials") from e

    record_audit_event(
        action="auth.login",
        outcome="success",
        actor_user_id=user.id,
        tenant_id=eff_tid,
        **_audit_req(request),
    )
    return _issue_token_bundle(request, db, settings, user=user, effective_tid=eff_tid, refresh_raw=refresh)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def post_change_password(
    request: Request,
    body: ChangePasswordIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> None:
    user = db.get(User, principal.user_id)
    if user is None or user.status != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token")
    if not verify_password(user.password_hash, body.current_password):
        record_audit_event(
            action="auth.password_change",
            outcome="failure",
            actor_user_id=principal.user_id,
            detail="invalid_password",
            **_audit_req(request),
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_current_password")
    try:
        assert_password_policy(body.new_password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    user.password_hash = hash_password(body.new_password)
    user.must_change_password = False
    db.add(user)
    db.commit()
    record_audit_event(
        action="auth.password_change",
        outcome="success",
        actor_user_id=principal.user_id,
        **_audit_req(request),
    )


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
    except ValueError as e:
        code = str(e)
        record_audit_event(
            action="auth.refresh",
            outcome="failure",
            detail=code,
            **_audit_req(request),
        )
        if code == "invalid_refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_refresh") from e
        if code == "platform_user_tenant_disallowed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="platform_user_tenant_disallowed",
            ) from e
        if code in ("tenant not allowed for user", "user has no tenant memberships"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="tenant_not_allowed") from e
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_refresh") from e

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
