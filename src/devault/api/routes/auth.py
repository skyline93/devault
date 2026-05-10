from __future__ import annotations

import secrets
import uuid
from dataclasses import replace
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from redis import Redis
from sqlalchemy import select
from sqlalchemy.orm import Session

from devault.api.deps import get_auth_context, get_db
from devault.api.schemas import (
    AuthLoginIn,
    AuthRegisterIn,
    AuthSessionOut,
    MfaEnrollConfirmIn,
    MfaEnrollStartOut,
    MfaVerifyIn,
    PasswordResetConfirmIn,
    PasswordResetRequestIn,
    TenantInvitationAcceptIn,
)
from devault.db.models import ConsoleUser, TenantMembership
from devault.security.auth_context import AuthContext
from devault.security.console_session_auth import (
    console_user_auth_context,
    resolve_effective_tenant_id_for_console_user,
)
from devault.security.http_session_store import (
    HttpSessionPayload,
    delete_session,
    load_session,
    new_session_id,
    save_session,
    touch_session_ttl,
    update_session_payload,
)
from devault.security.passwords import assert_password_policy, hash_password, verify_password
from devault.security.policy import authentication_enabled
from devault.security.totp_util import new_totp_secret, totp_uri, verify_totp
from devault.services.auth_audit import auth_audit
from devault.services.auth_session_payload import build_auth_session_out
from devault.services.console_login_policy import compute_new_session_mfa_verified
from devault.services.email_delivery import send_plain_email
from devault.services.login_rate_limit import check_sliding_rate_limit
from devault.services.password_reset_flow import create_reset_token, find_valid_reset_token, load_user_for_reset
from devault.services.sso_policy import console_user_password_login_blocked
from devault.services.tenant_invitation_flow import find_valid_invitation
from devault.settings import Settings, get_settings

router = APIRouter(prefix="/auth", tags=["auth"])

MFA_ENROLL_REDIS_PREFIX = "devault:mfa_enroll_secret:"


def _client_ip(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _set_csrf_cookie(response: Response, settings: Settings, token: str) -> None:
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=token,
        max_age=settings.session_ttl_seconds,
        httponly=False,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        path="/",
    )


def _set_session_cookie(response: Response, settings: Settings, session_id: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_id,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        path="/",
    )


@router.get(
    "/session",
    response_model=AuthSessionOut,
    summary="Current session principal",
    description=(
        "Returns the authenticated principal. Cookie session (human console) is evaluated before "
        "`Authorization: Bearer` (API key, legacy token, OIDC JWT). When authentication is disabled, "
        "returns the dev-open admin principal."
    ),
)
def get_auth_session(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
) -> AuthSessionOut:
    return build_auth_session_out(auth, db)


@router.get(
    "/csrf",
    summary="Issue CSRF cookie",
    description="Sets a readable CSRF cookie; send the same value as `X-CSRF-Token` on mutating requests when using a session cookie.",
)
def get_csrf_cookie(response: Response) -> dict[str, bool]:
    settings = get_settings()
    token = secrets.token_urlsafe(32)
    _set_csrf_cookie(response, settings, token)
    return {"ok": True}


@router.post("/session/refresh", summary="Refresh HTTP session TTL (sliding window)")
def post_session_refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
) -> dict[str, bool]:
    settings = get_settings()
    if auth.principal_kind != "tenant_user":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="only cookie sessions can refresh")
    sid = request.cookies.get(settings.session_cookie_name)
    if not sid or not touch_session_ttl(settings.redis_url, sid, settings.session_ttl_seconds):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="no valid session")
    _set_session_cookie(response, settings, sid)
    auth_audit("session_refresh", user_id=str(auth.user_id))
    return {"ok": True}


@router.post(
    "/login",
    response_model=AuthSessionOut,
    summary="Console email + password login",
)
def post_login(
    body: AuthLoginIn,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
) -> AuthSessionOut:
    settings = get_settings()
    if not authentication_enabled(settings, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="login disabled while authentication is not required (dev-open mode)",
        )
    ip = _client_ip(request)
    check_sliding_rate_limit(
        settings.redis_url,
        ip,
        max_per_minute=settings.auth_login_rate_limit_per_minute,
        key_prefix="devault:login_rl",
    )
    user = db.scalar(select(ConsoleUser).where(ConsoleUser.email == body.email))
    if user is None or not verify_password(user.password_hash, body.password):
        auth_audit("login", result="failure", email=body.email, client_ip=ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid email or password",
        )
    if user.disabled:
        auth_audit("login", result="disabled", email=body.email, client_ip=ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid email or password")

    if console_user_password_login_blocked(db, user):
        auth_audit("login", result="sso_password_disabled", email=body.email, client_ip=ip)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="password login disabled for this account (SSO-only tenants); use tenant OIDC Bearer",
        )

    try:
        mfa_ok = compute_new_session_mfa_verified(db, user)
    except HTTPException:
        auth_audit("login", result="mfa_enrollment_blocked", user_id=str(user.id), client_ip=ip)
        raise

    sid = new_session_id()
    save_session(
        settings.redis_url,
        sid,
        HttpSessionPayload(user_id=user.id, mfa_verified=mfa_ok),
        settings.session_ttl_seconds,
    )
    csrf = secrets.token_urlsafe(32)
    _set_session_cookie(response, settings, sid)
    _set_csrf_cookie(response, settings, csrf)

    x_tid = request.headers.get("X-DeVault-Tenant-Id")
    tid = resolve_effective_tenant_id_for_console_user(
        db,
        settings,
        x_devault_tenant_id=x_tid,
        user_id=user.id,
    )
    auth = console_user_auth_context(db, settings, user=user, effective_tenant_id=tid)
    auth = replace(auth, mfa_satisfied=mfa_ok)
    auth_audit("login", result="success", user_id=str(user.id), client_ip=ip, mfa_verified=mfa_ok)
    return build_auth_session_out(auth, db)


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Self-service console registration (optional)",
)
def post_register(
    body: AuthRegisterIn,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    settings = get_settings()
    if not settings.console_self_registration_enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="self-registration is disabled")
    if not authentication_enabled(settings, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="registration not available")
    ip = _client_ip(request)
    check_sliding_rate_limit(
        settings.redis_url,
        ip,
        max_per_minute=settings.auth_login_rate_limit_per_minute,
        key_prefix="devault:register_rl",
    )
    exists = db.scalar(select(ConsoleUser).where(ConsoleUser.email == body.email))
    if exists is not None:
        auth_audit("register", result="duplicate", email=body.email, client_ip=ip)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email already registered")
    assert_password_policy(body.password)
    u = ConsoleUser(email=body.email, password_hash=hash_password(body.password), disabled=False)
    db.add(u)
    db.commit()
    auth_audit("register", result="success", user_id=str(u.id), email=body.email, client_ip=ip)
    return {"detail": "account created; a platform administrator must grant tenant membership"}


@router.post(
    "/invitations/accept",
    response_model=AuthSessionOut,
    summary="Accept a tenant invitation (creates membership + console session)",
)
def post_invitation_accept(
    body: TenantInvitationAcceptIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthSessionOut:
    settings = get_settings()
    if not authentication_enabled(settings, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invitation accept not available")
    ip = _client_ip(request)
    check_sliding_rate_limit(
        settings.redis_url,
        ip,
        max_per_minute=settings.auth_login_rate_limit_per_minute,
        key_prefix="devault:invite_accept_rl",
    )

    inv = find_valid_invitation(db, body.token)
    if inv is None:
        auth_audit("invitation_accept", result="invalid_token", client_ip=ip)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid or expired invitation")

    cookie_uid: uuid.UUID | None = None
    sid0 = request.cookies.get(settings.session_cookie_name)
    if sid0:
        pl0 = load_session(settings.redis_url, sid0)
        if pl0 is not None:
            cookie_uid = pl0.user_id

    existing = db.scalar(select(ConsoleUser).where(ConsoleUser.email == inv.email))
    if existing is not None:
        if cookie_uid == existing.id:
            pass
        elif body.password is not None:
            if not verify_password(existing.password_hash, body.password):
                auth_audit("invitation_accept", result="bad_password", user_id=str(existing.id), client_ip=ip)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="invalid password for this invitation",
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="password required unless already signed in as the invited user",
            )
        user = existing
    else:
        if not body.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="password required to create your console account",
            )
        assert_password_policy(body.password)
        user = ConsoleUser(email=inv.email, password_hash=hash_password(body.password), disabled=False)
        db.add(user)
        db.flush()

    m = db.scalar(
        select(TenantMembership).where(
            TenantMembership.user_id == user.id,
            TenantMembership.tenant_id == inv.tenant_id,
        )
    )
    if m is None:
        db.add(TenantMembership(user_id=user.id, tenant_id=inv.tenant_id, role=inv.role))
    else:
        m.role = inv.role
    inv.accepted_at = datetime.now(timezone.utc)
    db.commit()

    try:
        mfa_ok = compute_new_session_mfa_verified(db, user)
    except HTTPException:
        auth_audit("invitation_accept", result="mfa_enrollment_blocked", user_id=str(user.id), client_ip=ip)
        raise

    if sid0:
        delete_session(settings.redis_url, sid0)
    sid = new_session_id()
    save_session(
        settings.redis_url,
        sid,
        HttpSessionPayload(user_id=user.id, mfa_verified=mfa_ok),
        settings.session_ttl_seconds,
    )
    csrf = secrets.token_urlsafe(32)
    _set_session_cookie(response, settings, sid)
    _set_csrf_cookie(response, settings, csrf)

    x_tid = request.headers.get("X-DeVault-Tenant-Id")
    tid = resolve_effective_tenant_id_for_console_user(
        db,
        settings,
        x_devault_tenant_id=x_tid,
        user_id=user.id,
    )
    auth = console_user_auth_context(db, settings, user=user, effective_tenant_id=tid)
    auth = replace(auth, mfa_satisfied=mfa_ok)
    auth_audit(
        "invitation_accept",
        result="success",
        user_id=str(user.id),
        tenant_id=str(inv.tenant_id),
        client_ip=ip,
        mfa_verified=mfa_ok,
    )
    return build_auth_session_out(auth, db)


@router.post("/password-reset/request", summary="Request password reset email (anti-enumeration)")
def post_password_reset_request(
    body: PasswordResetRequestIn,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    settings = get_settings()
    ip = _client_ip(request)
    check_sliding_rate_limit(
        settings.redis_url,
        ip,
        max_per_minute=settings.auth_login_rate_limit_per_minute,
        key_prefix="devault:pwreset_rl",
    )
    user = db.scalar(select(ConsoleUser).where(ConsoleUser.email == body.email))
    if user is not None and not user.disabled:
        raw = create_reset_token(db, user.id, ttl_minutes=settings.auth_password_reset_ttl_minutes)
        base = (settings.password_reset_link_base or "").rstrip("/")
        link = f"{base}/user/reset-password?token={raw}" if base else f"(set DEVAULT_PASSWORD_RESET_LINK_BASE) token={raw}"
        body_txt = (
            "You requested a password reset for DeVault.\n\n"
            f"Open this link (valid {settings.auth_password_reset_ttl_minutes} minutes):\n{link}\n"
        )
        send_plain_email(settings, to_addr=user.email, subject="DeVault password reset", body=body_txt)
        auth_audit("password_reset_request", result="issued", user_id=str(user.id), client_ip=ip)
    else:
        auth_audit("password_reset_request", result="no_user_or_disabled", email=body.email, client_ip=ip)
    return {"detail": "if the account exists, instructions were sent"}


@router.post("/password-reset/confirm", summary="Complete password reset with one-time token")
def post_password_reset_confirm(body: PasswordResetConfirmIn, request: Request, db: Session = Depends(get_db)) -> dict[str, str]:
    settings = get_settings()
    ip = _client_ip(request)
    row = find_valid_reset_token(db, body.token)
    if row is None:
        auth_audit("password_reset_confirm", result="invalid_token", client_ip=ip)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid or expired token")
    user = load_user_for_reset(db, row)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid or expired token")
    assert_password_policy(body.new_password)
    user.password_hash = hash_password(body.new_password)
    row.used_at = datetime.now(timezone.utc)
    db.commit()
    auth_audit("password_reset_confirm", result="success", user_id=str(user.id), client_ip=ip)
    return {"detail": "password updated"}


@router.post("/mfa/verify", response_model=AuthSessionOut, summary="Complete TOTP second factor after password login")
def post_mfa_verify(
    body: MfaVerifyIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthSessionOut:
    settings = get_settings()
    sid = request.cookies.get(settings.session_cookie_name)
    if not sid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="no session")
    payload = load_session(settings.redis_url, sid)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid session")
    user = db.get(ConsoleUser, payload.user_id)
    if user is None or user.disabled or not user.totp_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid mfa state")
    if not verify_totp(user.totp_secret, body.code):
        auth_audit("mfa_verify", result="failure", user_id=str(user.id), client_ip=_client_ip(request))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid totp code")
    new_pl = HttpSessionPayload(user_id=user.id, mfa_verified=True)
    if not update_session_payload(settings.redis_url, sid, new_pl, settings.session_ttl_seconds):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="session expired")
    csrf = secrets.token_urlsafe(32)
    _set_csrf_cookie(response, settings, csrf)
    x_tid = request.headers.get("X-DeVault-Tenant-Id")
    tid = resolve_effective_tenant_id_for_console_user(
        db,
        settings,
        x_devault_tenant_id=x_tid,
        user_id=user.id,
    )
    auth = console_user_auth_context(db, settings, user=user, effective_tenant_id=tid)
    auth = replace(auth, mfa_satisfied=True)
    auth_audit("mfa_verify", result="success", user_id=str(user.id), client_ip=_client_ip(request))
    return build_auth_session_out(auth, db)


@router.post("/mfa/enroll/start", response_model=MfaEnrollStartOut, summary="Begin TOTP enrollment (authenticated)")
def post_mfa_enroll_start(
    request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
) -> MfaEnrollStartOut:
    if auth.principal_kind != "tenant_user" or auth.user_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="console user required")
    if not auth.mfa_satisfied:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="complete MFA login first")
    user = db.get(ConsoleUser, auth.user_id)
    if user is None or user.totp_confirmed_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="totp already enrolled")
    secret = new_totp_secret()
    r = Redis.from_url(get_settings().redis_url, decode_responses=True)
    r.setex(f"{MFA_ENROLL_REDIS_PREFIX}{user.id}", 600, secret)
    uri = totp_uri(secret=secret, email=user.email)
    auth_audit("mfa_enroll_start", user_id=str(user.id), client_ip=_client_ip(request))
    return MfaEnrollStartOut(secret=secret, otpauth_uri=uri)


@router.post("/mfa/enroll/confirm", summary="Confirm TOTP enrollment with a valid code")
def post_mfa_enroll_confirm(
    body: MfaEnrollConfirmIn,
    request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
) -> dict[str, bool]:
    if auth.principal_kind != "tenant_user" or auth.user_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="console user required")
    if not auth.mfa_satisfied:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="complete MFA login first")
    settings = get_settings()
    r = Redis.from_url(settings.redis_url, decode_responses=True)
    secret = r.get(f"{MFA_ENROLL_REDIS_PREFIX}{auth.user_id}")
    if not secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="enrollment expired; start again")
    if not verify_totp(str(secret), body.code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid totp code")
    user = db.get(ConsoleUser, auth.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    user.totp_secret = str(secret)
    user.totp_confirmed_at = datetime.now(timezone.utc)
    db.commit()
    r.delete(f"{MFA_ENROLL_REDIS_PREFIX}{auth.user_id}")
    auth_audit("mfa_enroll_confirm", user_id=str(user.id), client_ip=_client_ip(request))
    return {"ok": True}


@router.post("/logout", summary="Invalidate server session and clear cookies")
def post_logout(request: Request, response: Response) -> dict[str, bool]:
    settings = get_settings()
    sid = request.cookies.get(settings.session_cookie_name)
    if sid:
        delete_session(settings.redis_url, sid)
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.delete_cookie(settings.csrf_cookie_name, path="/")
    auth_audit("logout", client_ip=_client_ip(request))
    return {"ok": True}
