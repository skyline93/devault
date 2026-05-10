"""Tenant-scoped Agent list (enrollment ∩ effective tenant + optional ``edge_agents`` snapshot)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from devault.api.deps import get_auth_context, get_db, get_effective_tenant
from devault.api.presenters import tenant_scoped_agents_for_tenant
from devault.api.schemas import TenantScopedAgentOut
from devault.db.models import Tenant
from devault.security.auth_context import AuthContext

router = APIRouter(prefix="/tenant-agents", tags=["tenant-agents"])


@router.get(
    "",
    response_model=list[TenantScopedAgentOut],
    summary="List Agents enrolled for the effective tenant (with fleet snapshot when known)",
)
def list_tenant_scoped_agents(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant),
    auth: AuthContext = Depends(get_auth_context),
) -> list[TenantScopedAgentOut]:
    del auth
    return tenant_scoped_agents_for_tenant(db, tenant.id)
