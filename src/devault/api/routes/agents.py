from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from devault.api.deps import get_auth_context, get_db, require_admin
from devault.api.presenters import edge_agent_to_out
from devault.api.schemas import EdgeAgentOut
from devault.db.models import EdgeAgent
from devault.security.agent_grpc_session import revoke_all_grpc_sessions_for_agent
from devault.security.auth_context import AuthContext
from devault.settings import get_settings

router = APIRouter(prefix="/agents", tags=["agents"])


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
    return [edge_agent_to_out(r) for r in rows]


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
    return edge_agent_to_out(row)


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
    if db.get(EdgeAgent, agent_id) is None:
        raise HTTPException(status_code=404, detail="agent not found")
    settings = get_settings()
    gen = revoke_all_grpc_sessions_for_agent(settings.redis_url, agent_id)
    return {"session_generation": gen}
