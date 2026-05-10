"""Agent enrollment: ``agent_id`` ↔ authorized tenants for Register and gRPC job isolation."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from devault.db.models import AgentEnrollment, Tenant


def get_enrollment(db: Session, agent_id: uuid.UUID) -> AgentEnrollment | None:
    return db.get(AgentEnrollment, agent_id)


def allowed_tenant_frozenset(row: AgentEnrollment | None) -> frozenset[uuid.UUID] | None:
    if row is None:
        return None
    out: list[uuid.UUID] = []
    for x in row.allowed_tenant_ids or []:
        out.append(uuid.UUID(str(x)))
    return frozenset(out)


def validate_tenant_ids_exist(db: Session, tenant_ids: list[uuid.UUID]) -> None:
    if not tenant_ids:
        raise ValueError("allowed_tenant_ids must contain at least one tenant")
    found = set(
        db.scalars(select(Tenant.id).where(Tenant.id.in_(tenant_ids))).all(),
    )
    missing = [tid for tid in tenant_ids if tid not in found]
    if missing:
        raise ValueError(f"unknown tenant_id(s): {missing}")


def upsert_enrollment(db: Session, agent_id: uuid.UUID, allowed_tenant_ids: list[uuid.UUID]) -> AgentEnrollment:
    validate_tenant_ids_exist(db, allowed_tenant_ids)
    raw = [str(x) for x in allowed_tenant_ids]
    now = datetime.now(timezone.utc)
    row = db.get(AgentEnrollment, agent_id)
    if row is None:
        row = AgentEnrollment(agent_id=agent_id, allowed_tenant_ids=raw, created_at=now, updated_at=now)
        db.add(row)
        return row
    row.allowed_tenant_ids = raw
    row.updated_at = now
    return row
