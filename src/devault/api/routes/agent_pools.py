from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from devault.api.deps import get_db, get_effective_tenant, require_write
from devault.api.schemas import (
    AgentPoolCreate,
    AgentPoolDetailOut,
    AgentPoolMemberOut,
    AgentPoolMembersPut,
    AgentPoolOut,
)
from devault.db.models import AgentPool, AgentPoolMember, EdgeAgent, Policy, Tenant
from devault.security.auth_context import AuthContext
from devault.services.policy_execution_binding import replace_pool_members

router = APIRouter(prefix="/agent-pools", tags=["agent-pools"])


def _build_pool_detail(db: Session, *, tenant_id: uuid.UUID, pool_id: uuid.UUID) -> AgentPoolDetailOut:
    pool = db.get(AgentPool, pool_id)
    if pool is None or pool.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="agent pool not found")
    members = list(
        db.scalars(select(AgentPoolMember).where(AgentPoolMember.pool_id == pool_id)).all(),
    )
    out_members: list[AgentPoolMemberOut] = []
    for m in sorted(members, key=lambda x: (x.sort_order, str(x.agent_id))):
        edge = db.get(EdgeAgent, m.agent_id)
        out_members.append(
            AgentPoolMemberOut(
                agent_id=m.agent_id,
                weight=m.weight,
                sort_order=m.sort_order,
                last_seen_at=edge.last_seen_at if edge else None,
            ),
        )
    return AgentPoolDetailOut(
        id=pool.id,
        tenant_id=pool.tenant_id,
        name=pool.name,
        created_at=pool.created_at,
        members=out_members,
    )


@router.post("", response_model=AgentPoolOut, summary="Create an Agent pool (tenant-scoped)")
def create_agent_pool(
    body: AgentPoolCreate,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant),
    _w: AuthContext = Depends(require_write),
) -> AgentPool:
    del _w
    pool = AgentPool(tenant_id=tenant.id, name=body.name.strip())
    db.add(pool)
    db.commit()
    db.refresh(pool)
    return pool


@router.get("", response_model=list[AgentPoolOut], summary="List Agent pools for the effective tenant")
def list_agent_pools(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant),
) -> list[AgentPool]:
    stmt = select(AgentPool).where(AgentPool.tenant_id == tenant.id).order_by(AgentPool.created_at.desc())
    return list(db.scalars(stmt).all())


@router.get("/{pool_id}", response_model=AgentPoolDetailOut, summary="Get pool with members and last-seen hints")
def get_agent_pool(
    pool_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant),
) -> AgentPoolDetailOut:
    return _build_pool_detail(db, tenant_id=tenant.id, pool_id=pool_id)


@router.put(
    "/{pool_id}/members",
    response_model=AgentPoolDetailOut,
    summary="Replace pool members (enrollment for tenant required per member)",
)
def put_agent_pool_members(
    pool_id: uuid.UUID,
    body: AgentPoolMembersPut,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant),
    _w: AuthContext = Depends(require_write),
) -> AgentPoolDetailOut:
    del _w
    tuples = [(m.agent_id, m.weight, m.sort_order) for m in body.members]
    replace_pool_members(db, pool_id, tenant_id=tenant.id, members=tuples)
    db.commit()
    return _build_pool_detail(db, tenant_id=tenant.id, pool_id=pool_id)


@router.delete("/{pool_id}", summary="Delete pool (clears policy bindings that reference it)")
def delete_agent_pool(
    pool_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant),
    _w: AuthContext = Depends(require_write),
) -> dict[str, str]:
    del _w
    pool = db.get(AgentPool, pool_id)
    if pool is None or pool.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="agent pool not found")
    db.execute(
        update(Policy)
        .where(Policy.tenant_id == tenant.id, Policy.bound_agent_pool_id == pool_id)
        .values(bound_agent_pool_id=None),
    )
    db.delete(pool)
    db.commit()
    return {"status": "deleted"}
