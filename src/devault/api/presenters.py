"""Shared shaping for API responses and HTML templates."""

from __future__ import annotations

from packaging.version import InvalidVersion, Version

from devault.api.schemas import EdgeAgentOut
from devault.db.models import EdgeAgent
from devault.release_meta import GRPC_API_PACKAGE
from devault.settings import get_settings


def edge_agent_to_out(row: EdgeAgent) -> EdgeAgentOut:
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
    )
