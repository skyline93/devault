from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from devault_iam.api.deps import get_db
from devault_iam.api.principal import Principal, ensure_tenant_scope, get_current_principal, require_permission
from devault_iam.db.models import Tenant, TenantMember, User
from devault_iam.services import permissions as perm_svc
from devault_iam.schemas.tenants import TenantCreateIn, TenantOut, TenantPatchIn

router = APIRouter(prefix="/v1/tenants", tags=["tenants"])


@router.get("", response_model=list[TenantOut])
def list_tenants(
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> list[Tenant]:
    if principal.is_platform_admin:
        require_permission(principal, "devault.platform.admin")
        return list(db.scalars(select(Tenant).order_by(Tenant.slug)).all())
    if not principal.tenant_ids:
        return []
    rows = list(
        db.scalars(select(Tenant).where(Tenant.id.in_(principal.tenant_ids)).order_by(Tenant.slug)).all()
    )
    return rows


@router.post("", response_model=TenantOut, status_code=status.HTTP_201_CREATED)
def create_tenant(
    body: TenantCreateIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> Tenant:
    require_permission(principal, "devault.platform.admin")
    slug = body.slug.strip().lower()
    if db.scalar(select(Tenant.id).where(Tenant.slug == slug)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="slug_taken")
    t = Tenant(name=body.name.strip(), slug=slug, plan="standard", status="active", owner_user_id=principal.user_id)
    db.add(t)
    db.flush()
    owner = db.get(User, principal.user_id)
    if owner is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="user_missing")
    if not owner.is_platform_admin:
        admin_role = perm_svc.get_template_role(db, "tenant_admin")
        if admin_role is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="rbac_seed_missing")
        db.add(
            TenantMember(
                tenant_id=t.id,
                user_id=principal.user_id,
                role_id=admin_role.id,
                status="active",
            )
        )
    db.commit()
    db.refresh(t)
    return t


@router.get("/{tenant_id}", response_model=TenantOut)
def get_tenant(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> Tenant:
    ensure_tenant_scope(principal, tenant_id)
    if "devault.console.read" not in principal.permissions:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    t = db.get(Tenant, tenant_id)
    if t is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant_not_found")
    return t


@router.patch("/{tenant_id}", response_model=TenantOut)
def patch_tenant(
    tenant_id: uuid.UUID,
    body: TenantPatchIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> Tenant:
    ensure_tenant_scope(principal, tenant_id)
    can = "devault.platform.admin" in principal.permissions or "devault.console.admin" in principal.permissions
    if not can:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    t = db.get(Tenant, tenant_id)
    if t is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant_not_found")
    if body.name is not None:
        t.name = body.name.strip()
    if body.plan is not None:
        if "devault.platform.admin" not in principal.permissions:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
        t.plan = body.plan.strip()
    if body.status is not None:
        if "devault.platform.admin" not in principal.permissions:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
        t.status = body.status.strip()
    db.add(t)
    db.commit()
    db.refresh(t)
    return t
