"""Persisted Agent fleet registry (Heartbeat/Register) and LeaseJobs version enforcement."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import grpc
from sqlalchemy.orm import Session

from devault.db.models import EdgeAgent
from devault.grpc.agent_version import (
    REASON_METADATA_KEY,
    evaluate_agent_version_gate,
)
from devault.settings import Settings


def upsert_edge_agent(
    db: Session,
    *,
    agent_id: uuid.UUID,
    agent_release: str | None,
    proto_package: str | None,
    git_commit: str | None,
    touch_register: bool = False,
) -> EdgeAgent:
    now = datetime.now(timezone.utc)
    rel = (agent_release or "").strip() or None
    pkg = (proto_package or "").strip() or None
    gc = (git_commit or "").strip() or None

    row = db.get(EdgeAgent, agent_id)
    if row is None:
        row = EdgeAgent(
            id=agent_id,
            first_seen_at=now,
            last_seen_at=now,
            agent_release=rel,
            proto_package=pkg,
            git_commit=gc,
            last_register_at=now if touch_register else None,
        )
        db.add(row)
        return row

    row.last_seen_at = now
    if rel is not None:
        row.agent_release = rel
    if pkg is not None:
        row.proto_package = pkg
    if gc is not None:
        row.git_commit = gc
    if touch_register:
        row.last_register_at = now
    return row


def enforce_edge_agent_for_lease(
    db: Session,
    *,
    agent_id: uuid.UUID,
    settings: Settings,
    context: grpc.ServicerContext,
    server_release: str,
) -> None:
    """Re-run version/proto gate using last Heartbeat fields (defense in depth for LeaseJobs)."""
    if not settings.grpc_enforce_version_on_lease:
        return

    row = db.get(EdgeAgent, agent_id)
    if row is None:
        context.set_trailing_metadata(((REASON_METADATA_KEY, "AGENT_REGISTRY_MISSING"),))
        context.abort(
            grpc.StatusCode.FAILED_PRECONDITION,
            "Agent registry missing; successful Heartbeat is required before LeaseJobs",
        )
        raise RuntimeError("unreachable")

    evaluate_agent_version_gate(
        agent_release=row.agent_release or "",
        proto_package=row.proto_package or "",
        settings=settings,
        context=context,
        server_release=server_release,
    )
