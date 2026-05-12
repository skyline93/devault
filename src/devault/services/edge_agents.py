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


def _norm_snapshot_str(value: str | None) -> str | None:
    if value is None:
        return None
    t = value.strip()
    return t or None


def _norm_allowlist(items: list[str] | None) -> list[str] | None:
    if not items:
        return None
    xs = sorted({str(x).strip().rstrip("/") for x in items if str(x).strip()})
    return xs or None


def upsert_edge_agent(
    db: Session,
    *,
    agent_id: uuid.UUID,
    agent_token_id: uuid.UUID | None = None,
    agent_release: str | None,
    proto_package: str | None,
    git_commit: str | None,
    touch_register: bool = False,
    snapshot_schema_version: int = 0,
    hostname: str | None = None,
    host_os: str | None = None,
    region: str | None = None,
    agent_env: str | None = None,
    backup_path_allowlist: list[str] | None = None,
) -> EdgeAgent:
    now = datetime.now(timezone.utc)
    rel = (agent_release or "").strip() or None
    pkg = (proto_package or "").strip() or None
    gc = (git_commit or "").strip() or None

    row = db.get(EdgeAgent, agent_id)
    if row is None:
        row = EdgeAgent(
            id=agent_id,
            agent_token_id=agent_token_id,
            first_seen_at=now,
            last_seen_at=now,
            agent_release=rel,
            proto_package=pkg,
            git_commit=gc,
            last_register_at=now if touch_register else None,
        )
        db.add(row)
    else:
        row.last_seen_at = now
        if agent_token_id is not None:
            row.agent_token_id = agent_token_id
        if rel is not None:
            row.agent_release = rel
        if pkg is not None:
            row.proto_package = pkg
        if gc is not None:
            row.git_commit = gc
        if touch_register:
            row.last_register_at = now

    if int(snapshot_schema_version or 0) >= 1:
        row.hostname = _norm_snapshot_str(hostname)
        row.host_os = _norm_snapshot_str(host_os)
        row.region = _norm_snapshot_str(region)
        row.agent_env = _norm_snapshot_str(agent_env)
        row.backup_path_allowlist = _norm_allowlist(backup_path_allowlist)

    return row


def touch_edge_agent_heartbeat(
    db: Session,
    *,
    agent_id: uuid.UUID,
    agent_release: str | None,
    proto_package: str | None,
    git_commit: str | None,
) -> EdgeAgent:
    """Refresh liveness; sync version columns when they change (no host snapshot updates)."""
    now = datetime.now(timezone.utc)
    row = db.get(EdgeAgent, agent_id)
    if row is None:
        raise ValueError("edge agent missing")
    row.last_seen_at = now
    rel = (agent_release or "").strip() or None
    pkg = (proto_package or "").strip() or None
    gc = (git_commit or "").strip() or None
    if rel is not None:
        row.agent_release = rel
    if pkg is not None:
        row.proto_package = pkg
    if gc is not None:
        row.git_commit = gc
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
