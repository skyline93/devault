"""Server capability tokens advertised on gRPC Heartbeat / Register replies."""

from __future__ import annotations

from devault.grpc_gen import agent_pb2
from devault.settings import Settings

# Canonical registry (documented in docs/compatibility.json → grpc.known_capabilities).
ALL_KNOWN_SERVER_CAPABILITIES: tuple[str, ...] = (
    "agent_grpc_v1",
    "backup_file_v1",
    "restore_file_v1",
    "s3_presign_bundle",
    "multipart_upload",
    "multipart_resume",
)


def compute_enabled_server_capabilities(settings: Settings) -> list[str]:
    """Subset of :data:`ALL_KNOWN_SERVER_CAPABILITIES` enabled for this control plane process."""
    caps: list[str] = [
        "agent_grpc_v1",
        "backup_file_v1",
        "restore_file_v1",
    ]
    if settings.storage_backend == "s3":
        caps.extend(
            (
                "s3_presign_bundle",
                "multipart_upload",
                "multipart_resume",
            )
        )
    return caps


def apply_server_capabilities(
    reply: agent_pb2.RegisterReply | agent_pb2.HeartbeatReply,
    settings: Settings,
) -> None:
    """Populate ``server_capabilities`` on Heartbeat / Register reply messages."""
    seq = compute_enabled_server_capabilities(settings)
    reply.server_capabilities[:] = seq
