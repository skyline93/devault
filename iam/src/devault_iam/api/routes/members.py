from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from devault_iam.api.deps import get_db
from devault_iam.api.principal import Principal, ensure_tenant_scope, get_current_principal, require_permission
from devault_iam.db.models import Role, TenantMember, User
from devault_iam.schemas.tenants import MemberCreateIn, MemberOut, MemberPatchIn
from devault_iam.services import permissions as perm_svc
from devault_iam.services.audit_service import record_audit_event
from devault_iam.services.permission_cache import invalidate_user_tenant
from devault_iam.settings import get_settings

router = APIRouter(prefix="/v1/tenants/{tenant_id}/members", tags=["members"])


def _audit_req(request: Request) -> dict:
    return {
        "request_id": getattr(request.state, "request_id", None),
        "ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    }


def _member_out(db: Session, m: TenantMember) -> MemberOut:
    u = db.get(User, m.user_id)
    r2 = db.get(Role, m.role_id)
    return MemberOut(
        id=m.id,
        user_id=m.user_id,
        email=u.email if u else "",
        role=r2.name if r2 else "",
        status=m.status,
    )


@router.get("", response_model=list[MemberOut])
def list_members(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> list[MemberOut]:
    ensure_tenant_scope(principal, tenant_id)
    if "devault.console.read" not in principal.permissions:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    rows = list(db.scalars(select(TenantMember).where(TenantMember.tenant_id == tenant_id)).all())
    return [_member_out(db, m) for m in rows]


@router.post("", response_model=MemberOut, status_code=status.HTTP_201_CREATED)
def add_member(
    request: Request,
    tenant_id: uuid.UUID,
    body: MemberCreateIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> MemberOut:
    ensure_tenant_scope(principal, tenant_id)
    require_permission(principal, "devault.console.admin")
    email = body.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")
    role = perm_svc.get_template_role(db, body.role)
    if role is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_role")
    if db.scalar(
        select(TenantMember.id).where(
            TenantMember.tenant_id == tenant_id,
            TenantMember.user_id == user.id,
        )
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="already_member")
    m = TenantMember(tenant_id=tenant_id, user_id=user.id, role_id=role.id, status="active")
    db.add(m)
    db.commit()
    db.refresh(m)
    invalidate_user_tenant(get_settings().redis_url, tenant_id, user.id)
    record_audit_event(
        action="tenant.member.create",
        outcome="success",
        actor_user_id=principal.user_id,
        tenant_id=tenant_id,
        resource_type="tenant_member",
        resource_id=str(m.id),
        context={"target_user_id": str(user.id), "role": body.role},
        **_audit_req(request),
    )
    return _member_out(db, m)


@router.patch("/{member_id}", response_model=MemberOut)
def patch_member(
    request: Request,
    tenant_id: uuid.UUID,
    member_id: uuid.UUID,
    body: MemberPatchIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> MemberOut:
    ensure_tenant_scope(principal, tenant_id)
    require_permission(principal, "devault.console.admin")
    m = db.get(TenantMember, member_id)
    if m is None or m.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="member_not_found")
    role = perm_svc.get_template_role(db, body.role)
    if role is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_role")
    m.role_id = role.id
    db.add(m)
    db.commit()
    db.refresh(m)
    invalidate_user_tenant(get_settings().redis_url, tenant_id, m.user_id)
    record_audit_event(
        action="tenant.member.update",
        outcome="success",
        actor_user_id=principal.user_id,
        tenant_id=tenant_id,
        resource_type="tenant_member",
        resource_id=str(m.id),
        context={"target_user_id": str(m.user_id), "role": body.role},
        **_audit_req(request),
    )
    return _member_out(db, m)


@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member(
    request: Request,
    tenant_id: uuid.UUID,
    member_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> None:
    ensure_tenant_scope(principal, tenant_id)
    require_permission(principal, "devault.console.admin")
    m = db.get(TenantMember, member_id)
    if m is None or m.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="member_not_found")
    if m.user_id == principal.user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="cannot_remove_self")
    uid = m.user_id
    mid = m.id
    db.delete(m)
    db.commit()
    invalidate_user_tenant(get_settings().redis_url, tenant_id, uid)
    record_audit_event(
        action="tenant.member.remove",
        outcome="success",
        actor_user_id=principal.user_id,
        tenant_id=tenant_id,
        resource_type="tenant_member",
        resource_id=str(mid),
        context={"removed_user_id": str(uid)},
        **_audit_req(request),
    )
