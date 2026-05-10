from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from devault_iam.api.deps import get_db
from devault_iam.api.principal import Principal, get_current_principal
from devault_iam.schemas.auth import MfaConfirmIn, MfaDisableIn, MfaEnrollStartOut
from devault_iam.services import auth_service
from devault_iam.services.audit_service import record_audit_event
from devault_iam.services.permissions import load_user_active

router = APIRouter(prefix="/v1/auth/mfa", tags=["mfa"])


def _audit_req(request: Request) -> dict:
    return {
        "request_id": getattr(request.state, "request_id", None),
        "ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    }


@router.post("/enroll/start", response_model=MfaEnrollStartOut)
def mfa_enroll_start(
    request: Request,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> MfaEnrollStartOut:
    user = load_user_active(db, principal.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user_inactive")
    try:
        secret, uri = auth_service.start_mfa_enrollment(user)
    except ValueError as e:
        if str(e) == "mfa_already_enabled":
            record_audit_event(
                action="mfa.enroll.start",
                outcome="failure",
                actor_user_id=principal.user_id,
                tenant_id=principal.tenant_id,
                detail="mfa_already_enabled",
                **_audit_req(request),
            )
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="mfa_already_enabled") from e
        raise
    record_audit_event(
        action="mfa.enroll.start",
        outcome="success",
        actor_user_id=principal.user_id,
        tenant_id=principal.tenant_id,
        **_audit_req(request),
    )
    return MfaEnrollStartOut(secret=secret, otpauth_uri=uri)


@router.post("/enroll/confirm", status_code=status.HTTP_204_NO_CONTENT)
def mfa_enroll_confirm(
    request: Request,
    body: MfaConfirmIn,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> None:
    user = load_user_active(db, principal.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user_inactive")
    try:
        auth_service.confirm_mfa_enrollment(db, user, body.secret, body.code)
    except ValueError as e:
        if str(e) == "mfa_invalid":
            record_audit_event(
                action="mfa.enroll.confirm",
                outcome="failure",
                actor_user_id=principal.user_id,
                tenant_id=principal.tenant_id,
                detail="mfa_invalid",
                **_audit_req(request),
            )
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="mfa_invalid") from e
        raise
    record_audit_event(
        action="mfa.enroll.confirm",
        outcome="success",
        actor_user_id=principal.user_id,
        tenant_id=principal.tenant_id,
        **_audit_req(request),
    )


@router.post("/disable", status_code=status.HTTP_204_NO_CONTENT)
def mfa_disable(
    request: Request,
    body: MfaDisableIn,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> None:
    user = load_user_active(db, principal.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user_inactive")
    try:
        auth_service.disable_mfa(db, user, body.password, body.code)
    except ValueError as e:
        code = str(e)
        record_audit_event(
            action="mfa.disable",
            outcome="failure",
            actor_user_id=principal.user_id,
            tenant_id=principal.tenant_id,
            detail=code,
            **_audit_req(request),
        )
        if code == "invalid_password":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid_password") from e
        if code in ("mfa_invalid", "mfa_not_enabled"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=code) from e
        raise
    record_audit_event(
        action="mfa.disable",
        outcome="success",
        actor_user_id=principal.user_id,
        tenant_id=principal.tenant_id,
        **_audit_req(request),
    )
