"""Validate policy execution binding (single Agent vs pool) and pool membership enrollments."""

from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import delete
from sqlalchemy.orm import Session

from devault.db.models import AgentPool, AgentPoolMember
from devault.services.agent_enrollment import allowed_tenant_frozenset, get_enrollment


def validate_policy_execution_binding(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    bound_agent_id: uuid.UUID | None,
    bound_agent_pool_id: uuid.UUID | None,
) -> None:
    """At most one of ``bound_agent_id`` / ``bound_agent_pool_id``; each must be valid for ``tenant_id``."""
    if bound_agent_id is not None and bound_agent_pool_id is not None:
        raise HTTPException(
            status_code=400,
            detail="only one of bound_agent_id or bound_agent_pool_id may be set",
        )
    if bound_agent_id is not None:
        enr = get_enrollment(db, bound_agent_id)
        if enr is None:
            raise HTTPException(
                status_code=400,
                detail="bound_agent_id requires an existing agent_enrollment row",
            )
        allowed = allowed_tenant_frozenset(enr)
        if not allowed or tenant_id not in allowed:
            raise HTTPException(
                status_code=400,
                detail="bound_agent_id is not enrolled for this policy tenant",
            )
    if bound_agent_pool_id is not None:
        pool = db.get(AgentPool, bound_agent_pool_id)
        if pool is None or pool.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail="bound_agent_pool_id not found for this tenant")


def validate_pool_member_enrollments(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    agent_ids: list[uuid.UUID],
) -> None:
    """Each pool member must be enrolled for ``tenant_id`` (same rule as bound_agent_id)."""
    if not agent_ids:
        return
    seen: set[uuid.UUID] = set()
    for aid in agent_ids:
        if aid in seen:
            raise HTTPException(status_code=400, detail=f"duplicate agent_id in pool: {aid}")
        seen.add(aid)
        enr = get_enrollment(db, aid)
        if enr is None:
            raise HTTPException(
                status_code=400,
                detail=f"pool member {aid} has no agent_enrollment",
            )
        allowed = allowed_tenant_frozenset(enr)
        if not allowed or tenant_id not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"pool member {aid} is not enrolled for this tenant",
            )


def replace_pool_members(
    db: Session,
    pool_id: uuid.UUID,
    *,
    tenant_id: uuid.UUID,
    members: list[tuple[uuid.UUID, int, int]],
) -> list[AgentPoolMember]:
    """Replace all members with ``(agent_id, weight, sort_order)`` rows."""
    pool = db.get(AgentPool, pool_id)
    if pool is None or pool.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="agent pool not found")
    aids = [m[0] for m in members]
    validate_pool_member_enrollments(db, tenant_id=tenant_id, agent_ids=aids)
    db.execute(delete(AgentPoolMember).where(AgentPoolMember.pool_id == pool_id))
    rows: list[AgentPoolMember] = []
    for agent_id, weight, sort_order in members:
        rows.append(
            AgentPoolMember(
                pool_id=pool_id,
                agent_id=agent_id,
                weight=max(1, int(weight)),
                sort_order=int(sort_order),
            )
        )
    db.add_all(rows)
    return rows
