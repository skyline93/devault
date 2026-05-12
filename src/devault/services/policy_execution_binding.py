"""Validate policy execution binding to a registered edge Agent for the policy tenant."""

from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from devault.db.models import AgentToken, EdgeAgent


def validate_bound_agent_for_policy(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    bound_agent_id: uuid.UUID,
) -> None:
    edge = db.get(EdgeAgent, bound_agent_id)
    if edge is None or edge.agent_token_id is None:
        raise HTTPException(
            status_code=400,
            detail="bound_agent_id must reference a registered edge Agent",
        )
    token = db.get(AgentToken, edge.agent_token_id)
    if token is None:
        raise HTTPException(status_code=400, detail="bound_agent_id token missing")
    if token.tenant_id != tenant_id:
        raise HTTPException(
            status_code=400,
            detail="bound_agent_id is not registered for this policy tenant",
        )
    if token.disabled_at is not None:
        raise HTTPException(status_code=400, detail="bound_agent_id token is disabled")
