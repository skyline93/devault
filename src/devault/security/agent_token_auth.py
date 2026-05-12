"""Authenticate Agent gRPC Bearer tokens against ``agent_tokens``."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import grpc
from sqlalchemy.orm import Session

from devault.db.models import AgentToken, EdgeAgent
from devault.security.auth_context import AuthContext
from devault.services.agent_tokens import (
    agent_token_is_usable,
    get_agent_token_by_hash,
    hash_agent_token,
    touch_agent_token_used,
)


@dataclass(frozen=True, slots=True)
class AgentTokenPrincipal:
    token: AgentToken
    tenant_id: uuid.UUID


def authenticate_agent_bearer(db: Session, raw_token: str) -> AgentTokenPrincipal | None:
    token = raw_token.strip()
    if not token:
        return None
    row = get_agent_token_by_hash(db, hash_agent_token(token))
    if row is None or not agent_token_is_usable(row):
        return None
    touch_agent_token_used(db, row)
    return AgentTokenPrincipal(token=row, tenant_id=row.tenant_id)


def auth_context_from_agent_token(principal: AgentTokenPrincipal) -> AuthContext:
    tid = principal.tenant_id
    return AuthContext(
        role="operator",
        allowed_tenant_ids=frozenset({tid}),
        principal_label=f"agent-token:{principal.token.id}",
        principal_kind="platform",
    )


def abort_unauthenticated(context: grpc.ServicerContext, detail: str) -> None:
    context.abort(grpc.StatusCode.UNAUTHENTICATED, detail)
    raise RuntimeError("unreachable")


def require_agent_token(
    db: Session,
    context: grpc.ServicerContext,
    raw_token: str,
) -> AgentTokenPrincipal:
    principal = authenticate_agent_bearer(db, raw_token)
    if principal is None:
        abort_unauthenticated(context, "invalid or disabled agent token")
    assert principal is not None
    return principal


def edge_agent_belongs_to_token(edge: EdgeAgent | None, token_id: uuid.UUID) -> bool:
    return edge is not None and edge.agent_token_id == token_id


def ensure_agent_instance_for_token(
    db: Session,
    *,
    agent_id: uuid.UUID,
    token_id: uuid.UUID,
    context: grpc.ServicerContext,
) -> EdgeAgent:
    row = db.get(EdgeAgent, agent_id)
    if row is None:
        context.abort(grpc.StatusCode.PERMISSION_DENIED, "unknown agent_id for this token")
        raise RuntimeError("unreachable")
    if row.agent_token_id != token_id:
        context.abort(grpc.StatusCode.PERMISSION_DENIED, "agent_id is not registered for this token")
        raise RuntimeError("unreachable")
    return row
