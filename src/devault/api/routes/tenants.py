from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from devault.api.deps import (
    ensure_platform_or_tenant_admin_for_tenant,
    get_auth_context,
    get_db,
    require_admin,
)
from devault.api.schemas import TenantCreate, TenantOut, TenantPatch
from devault.db.models import Tenant
from devault.security.auth_context import AuthContext
from devault.services import control as control_svc

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.get("", response_model=list[TenantOut], summary="List tenants")
def list_tenants(
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
) -> list[Tenant]:
    if auth.allowed_tenant_ids is not None and not auth.allowed_tenant_ids:
        return []
    stmt = select(Tenant).order_by(Tenant.slug.asc())
    if auth.allowed_tenant_ids is not None:
        stmt = stmt.where(Tenant.id.in_(auth.allowed_tenant_ids))
    return list(db.scalars(stmt).all())


@router.post("", response_model=TenantOut, summary="Create tenant")
def create_tenant(
    body: TenantCreate,
    db: Session = Depends(get_db),
    _a: AuthContext = Depends(require_admin),
) -> Tenant:
    return control_svc.create_tenant(db, body)


@router.patch("/{tenant_id}", response_model=TenantOut, summary="Update tenant (admin)")
def patch_tenant(
    tenant_id: uuid.UUID,
    body: TenantPatch,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
) -> Tenant:
    ensure_platform_or_tenant_admin_for_tenant(auth, tenant_id)
    return control_svc.patch_tenant(db, tenant_id, body)
