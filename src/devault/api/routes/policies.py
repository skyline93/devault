from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from devault.api.deps import get_db, get_effective_tenant, require_write
from devault.api.schemas import PolicyCreate, PolicyOut, PolicyPatch
from devault.db.models import Policy, Tenant
from devault.security.auth_context import AuthContext
from devault.services import control as control_svc

router = APIRouter(prefix="/policies", tags=["policies"])


@router.post("", response_model=PolicyOut, summary="Create policy")
def create_policy(
    body: PolicyCreate,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant),
    _w: AuthContext = Depends(require_write),
) -> Policy:
    return control_svc.create_policy(db, body, tenant_id=tenant.id)


@router.get("", response_model=list[PolicyOut], summary="List policies")
def list_policies(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant),
) -> list[Policy]:
    stmt = select(Policy).where(Policy.tenant_id == tenant.id).order_by(Policy.created_at.desc())
    return list(db.scalars(stmt).all())


@router.get("/{policy_id}", response_model=PolicyOut, summary="Get policy")
def get_policy(
    policy_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant),
) -> Policy:
    p = db.get(Policy, policy_id)
    if p is None or p.tenant_id != tenant.id:
        raise HTTPException(404, detail="policy not found")
    return p


@router.patch("/{policy_id}", response_model=PolicyOut, summary="Update policy")
def patch_policy(
    policy_id: uuid.UUID,
    body: PolicyPatch,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant),
    _w: AuthContext = Depends(require_write),
) -> Policy:
    return control_svc.patch_policy(db, policy_id, body, tenant_id=tenant.id)


@router.delete("/{policy_id}", summary="Delete policy")
def delete_policy(
    policy_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant),
    _w: AuthContext = Depends(require_write),
) -> dict[str, str]:
    control_svc.delete_policy(db, policy_id, tenant_id=tenant.id)
    return {"status": "deleted"}
