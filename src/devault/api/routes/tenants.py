from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from devault.api.deps import get_auth_context, get_db, require_admin
from devault.api.schemas import TenantCreate, TenantOut
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
