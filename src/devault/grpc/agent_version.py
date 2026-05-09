"""gRPC Heartbeat / Register: Agent vs control plane release and proto package negotiation."""

from __future__ import annotations

import logging

import grpc
from packaging.version import InvalidVersion, Version

from devault import __version__
from devault.grpc_gen import agent_pb2
from devault.release_meta import GRPC_API_PACKAGE
from devault.settings import Settings

logger = logging.getLogger(__name__)

EXPECTED_PROTO_PACKAGE = GRPC_API_PACKAGE
REASON_METADATA_KEY = "devault-reason-code"


def effective_max_tested(settings: Settings, server_release: str) -> str:
    raw = (settings.grpc_max_tested_agent_version or "").strip()
    return raw or server_release


def attach_control_plane_version_meta(
    reply: agent_pb2.RegisterReply | agent_pb2.HeartbeatReply,
    settings: Settings,
) -> None:
    sr = __version__
    reply.server_release = sr
    reply.min_supported_agent_version = settings.grpc_min_supported_agent_version
    reply.max_tested_agent_version = effective_max_tested(settings, sr)
    if settings.grpc_upgrade_url:
        reply.upgrade_url = settings.grpc_upgrade_url


def _abort_with_reason(
    context: grpc.ServicerContext,
    *,
    code: grpc.StatusCode,
    details: str,
    reason: str,
) -> None:
    context.set_trailing_metadata(((REASON_METADATA_KEY, reason),))
    context.abort(code, details)
    raise RuntimeError("unreachable")


def evaluate_agent_version_gate(
    *,
    agent_release: str,
    proto_package: str,
    settings: Settings,
    context: grpc.ServicerContext,
    server_release: str,
) -> str:
    """Return ``deprecation_message`` (possibly empty). Aborts RPC on hard failures."""
    pp = (proto_package or "").strip()
    if pp and pp != EXPECTED_PROTO_PACKAGE:
        _abort_with_reason(
            context,
            code=grpc.StatusCode.FAILED_PRECONDITION,
            details=(
                f"unsupported gRPC proto package {pp!r}; "
                f"rebuild Agent against {EXPECTED_PROTO_PACKAGE}"
            ),
            reason="AGENT_PROTO_PACKAGE_MISMATCH",
        )

    rel = (agent_release or "").strip()
    if not rel:
        if settings.grpc_require_agent_version:
            _abort_with_reason(
                context,
                code=grpc.StatusCode.FAILED_PRECONDITION,
                details=(
                    "agent_release is required on Heartbeat/Register; "
                    "set DEVAULT_GRPC_REQUIRE_AGENT_VERSION=false to allow legacy agents"
                ),
                reason="AGENT_VERSION_REQUIRED",
            )
        logger.info("gRPC version gate: missing agent_release (legacy agent), allowing")
        return (
            "Agent did not send agent_release; upgrade when possible for version negotiation."
        )

    try:
        av = Version(rel)
    except InvalidVersion:
        _abort_with_reason(
            context,
            code=grpc.StatusCode.INVALID_ARGUMENT,
            details=f"unparseable agent_release: {rel!r}",
            reason="AGENT_VERSION_UNPARSEABLE",
        )

    try:
        min_v = Version(settings.grpc_min_supported_agent_version)
    except InvalidVersion as e:
        raise RuntimeError(
            f"invalid DEVAULT_GRPC_MIN_SUPPORTED_AGENT_VERSION: {e}"
        ) from e

    max_s = effective_max_tested(settings, server_release)
    try:
        max_v = Version(max_s)
    except InvalidVersion as e:
        raise RuntimeError(f"invalid DEVAULT_GRPC_MAX_TESTED_AGENT_VERSION: {e}") from e

    if av < min_v:
        _abort_with_reason(
            context,
            code=grpc.StatusCode.FAILED_PRECONDITION,
            details=(
                f"agent_release {rel} is below minimum supported "
                f"{settings.grpc_min_supported_agent_version}"
            ),
            reason="AGENT_VERSION_TOO_OLD",
        )

    if av > max_v:
        msg = (
            f"agent_release {rel} is newer than max tested {max_s}; "
            "continuing with best-effort compatibility"
        )
        logger.warning("gRPC version gate: %s", msg)
        return msg

    return ""
