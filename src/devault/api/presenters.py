"""Shared shaping for API responses and HTML templates."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from packaging.version import InvalidVersion, Version
from sqlalchemy import select
from sqlalchemy.orm import Session

from devault.api.schemas import EdgeAgentOut, TenantScopedAgentOut
from devault.db.models import AgentEnrollment, EdgeAgent
from devault.release_meta import GRPC_API_PACKAGE
from devault.services.tenant_backup_allowlist import list_enrolled_agent_ids_for_tenant
from devault.settings import get_settings


def edge_agent_to_out(
    row: EdgeAgent,
    *,
    allowed_tenant_ids: list[uuid.UUID] | None = None,
) -> EdgeAgentOut:
    settings = get_settings()
    meets = True
    ar = (row.agent_release or "").strip()
    if ar:
        try:
            meets = Version(ar) >= Version(settings.grpc_min_supported_agent_version)
        except InvalidVersion:
            meets = False
    pp = (row.proto_package or "").strip()
    proto_ok = not pp or pp == GRPC_API_PACKAGE
    bl = row.backup_path_allowlist
    allowlist = [str(x) for x in bl] if bl else None
    return EdgeAgentOut(
        id=row.id,
        first_seen_at=row.first_seen_at,
        last_seen_at=row.last_seen_at,
        agent_release=row.agent_release,
        proto_package=row.proto_package,
        git_commit=row.git_commit,
        last_register_at=row.last_register_at,
        meets_min_supported_version=meets,
        proto_matches_control_plane=proto_ok,
        allowed_tenant_ids=allowed_tenant_ids,
        hostname=row.hostname,
        os=row.host_os,
        region=row.region,
        env=row.agent_env,
        backup_path_allowlist=allowlist,
    )


def tenant_scoped_agents_for_tenant(db: Session, tenant_id: uuid.UUID) -> list[TenantScopedAgentOut]:
    """Agents with enrollment listing ``tenant_id``, merged with ``edge_agents`` when present."""
    enrolled_ids = list_enrolled_agent_ids_for_tenant(db, tenant_id)
    if not enrolled_ids:
        return []
    enr_rows = list(
        db.scalars(select(AgentEnrollment).where(AgentEnrollment.agent_id.in_(enrolled_ids))).all()
    )
    enr_by_id = {e.agent_id: e for e in enr_rows}
    out: list[TenantScopedAgentOut] = []
    for aid in enrolled_ids:
        enr = enr_by_id.get(aid)
        if enr is None:
            continue
        allowed = [uuid.UUID(str(x)) for x in (enr.allowed_tenant_ids or [])]
        edge = db.get(EdgeAgent, aid)
        if edge is None:
            out.append(
                TenantScopedAgentOut(
                    id=aid,
                    allowed_tenant_ids=allowed,
                )
            )
            continue
        base = edge_agent_to_out(edge, allowed_tenant_ids=allowed)
        out.append(
            TenantScopedAgentOut(
                id=base.id,
                allowed_tenant_ids=allowed,
                first_seen_at=base.first_seen_at,
                last_seen_at=base.last_seen_at,
                agent_release=base.agent_release,
                proto_package=base.proto_package,
                git_commit=base.git_commit,
                last_register_at=base.last_register_at,
                meets_min_supported_version=base.meets_min_supported_version,
                proto_matches_control_plane=base.proto_matches_control_plane,
                hostname=base.hostname,
                os=base.os,
                region=base.region,
                env=base.env,
                backup_path_allowlist=base.backup_path_allowlist,
            )
        )
    _far_past = datetime(1970, 1, 1, tzinfo=timezone.utc)
    out.sort(key=lambda x: x.last_seen_at if x.last_seen_at is not None else _far_past, reverse=True)
    return out
