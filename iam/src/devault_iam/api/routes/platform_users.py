from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from devault_iam.api.deps import get_db
from devault_iam.api.principal import Principal, get_current_principal, require_platform_admin_identity
from devault_iam.db.models import User
from devault_iam.schemas.platform_users import PlatformUserCreateIn, PlatformUserOut, PlatformUserPatchIn
from devault_iam.security.passwords import hash_password
from devault_iam.services.audit_service import record_audit_event
router = APIRouter(prefix="/v1/platform/users", tags=["platform-users"])


def _audit_req(request: Request) -> dict:
    return {
        "request_id": getattr(request.state, "request_id", None),
        "ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    }


@router.post("", response_model=PlatformUserOut, status_code=status.HTTP_201_CREATED)
def create_platform_managed_user(
    request: Request,
    body: PlatformUserCreateIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> User:
    require_platform_admin_identity(principal)
    email_n = str(body.email).strip().lower()
    if db.scalar(select(User.id).where(User.email == email_n)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email_taken")
    try:
        pw_hash = hash_password(body.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    name = (body.name or "").strip() or email_n.split("@", 1)[0]
    u = User(
        email=email_n,
        password_hash=pw_hash,
        name=name,
        status="active",
        is_platform_admin=False,
        must_change_password=bool(body.must_change_password),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    record_audit_event(
        action="platform.user.create",
        outcome="success",
        actor_user_id=principal.user_id,
        resource_type="user",
        resource_id=str(u.id),
        context={"email": email_n},
        **_audit_req(request),
    )
    return u


@router.patch("/{user_id}", response_model=PlatformUserOut)
def patch_platform_managed_user(
    request: Request,
    user_id: uuid.UUID,
    body: PlatformUserPatchIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> User:
    require_platform_admin_identity(principal)
    u = db.get(User, user_id)
    if u is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")
    if u.is_platform_admin:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="cannot_modify_platform_identity")
    if body.password is None and body.must_change_password is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="empty_patch")
    if body.password is not None:
        try:
            u.password_hash = hash_password(body.password)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
        if body.must_change_password is None:
            u.must_change_password = False
    if body.must_change_password is not None:
        u.must_change_password = body.must_change_password
    db.add(u)
    db.commit()
    db.refresh(u)
    record_audit_event(
        action="platform.user.update",
        outcome="success",
        actor_user_id=principal.user_id,
        resource_type="user",
        resource_id=str(u.id),
        context={
            "set_password": body.password is not None,
            "must_change_password": body.must_change_password,
        },
        **_audit_req(request),
    )
    return u
