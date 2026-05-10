from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from devault.api.deps import get_auth_context, get_db, require_admin
from devault.api.presenters import edge_agent_to_out
from devault.api.schemas import AgentEnrollmentOut, AgentEnrollmentPut, EdgeAgentOut
from devault.db.models import AgentEnrollment, EdgeAgent
from devault.security.agent_grpc_session import revoke_all_grpc_sessions_for_agent
from devault.security.auth_context import AuthContext
from devault.services.agent_enrollment import get_enrollment, upsert_enrollment
from devault.settings import get_settings

router = APIRouter(prefix="/agents", tags=["agents"])


def _allowed_ids_from_row(enr: AgentEnrollment | None) -> list[uuid.UUID] | None:
    if enr is None:
        return None
    return [uuid.UUID(str(x)) for x in (enr.allowed_tenant_ids or [])]


@router.get("", response_model=list[EdgeAgentOut], summary="List edge Agents (fleet inventory)")
def list_agents(
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[EdgeAgentOut]:
    del auth  # ensures Bearer / API key / OIDC present
    stmt = select(EdgeAgent).order_by(EdgeAgent.last_seen_at.desc()).limit(limit).offset(offset)
    rows = list(db.scalars(stmt).all())
    ids = [r.id for r in rows]
    enr_map: dict[uuid.UUID, AgentEnrollment] = {}
    if ids:
        enr_rows = list(db.scalars(select(AgentEnrollment).where(AgentEnrollment.agent_id.in_(ids))).all())
        enr_map = {e.agent_id: e for e in enr_rows}
    return [
        edge_agent_to_out(r, allowed_tenant_ids=_allowed_ids_from_row(enr_map.get(r.id)))
        for r in rows
    ]


@router.get(
    "/{agent_id}/enrollment",
    response_model=AgentEnrollmentOut,
    summary="Get Agent tenant enrollment (authorized tenant UUIDs for gRPC)",
)
def get_agent_enrollment(
    agent_id: uuid.UUID,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
) -> AgentEnrollmentOut:
    del auth
    row = get_enrollment(db, agent_id)
    if row is None:
        raise HTTPException(status_code=404, detail="agent enrollment not found")
    return AgentEnrollmentOut.model_validate(row)


@router.put(
    "/{agent_id}/enrollment",
    response_model=AgentEnrollmentOut,
    summary="Set or replace Agent tenant enrollment (admin)",
)
def put_agent_enrollment(
    agent_id: uuid.UUID,
    body: AgentEnrollmentPut,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_admin),
) -> AgentEnrollmentOut:
    del auth
    row = upsert_enrollment(db, agent_id, list(body.allowed_tenant_ids))
    db.commit()
    db.refresh(row)
    return AgentEnrollmentOut.model_validate(row)


@router.get("/{agent_id}", response_model=EdgeAgentOut, summary="Get one Agent by id")
def get_agent(
    agent_id: uuid.UUID,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
) -> EdgeAgentOut:
    del auth
    row = db.get(EdgeAgent, agent_id)
    if row is None:
        raise HTTPException(status_code=404, detail="agent not found")
    enr = get_enrollment(db, agent_id)
    return edge_agent_to_out(row, allowed_tenant_ids=_allowed_ids_from_row(enr))


@router.post(
    "/{agent_id}/revoke-grpc-sessions",
    summary="Revoke Register-minted gRPC bearer tokens for this Agent (Redis)",
)
def revoke_agent_grpc_sessions(
    agent_id: uuid.UUID,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_admin),
) -> dict[str, int]:
    """Bump session generation so all per-Agent Bearer tokens minted via Register become invalid."""
    del auth
    if db.get(EdgeAgent, agent_id) is None and get_enrollment(db, agent_id) is None:
        raise HTTPException(status_code=404, detail="agent not found")
    settings = get_settings()
    gen = revoke_all_grpc_sessions_for_agent(settings.redis_url, agent_id)
    return {"session_generation": gen}
