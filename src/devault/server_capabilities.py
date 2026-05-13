"""Server capability tokens advertised on gRPC Heartbeat / Register replies."""

from __future__ import annotations

from sqlalchemy.orm import Session

from devault.db.session import SessionLocal
from devault.grpc_gen import agent_pb2
from devault.services.storage_profiles import get_active_profile
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


def compute_enabled_server_capabilities(_settings: Settings, db: Session) -> list[str]:
    """Subset of :data:`ALL_KNOWN_SERVER_CAPABILITIES` enabled for this control plane process."""
    caps: list[str] = [
        "agent_grpc_v1",
        "backup_file_v1",
        "restore_file_v1",
    ]
    prof = get_active_profile(db)
    if prof is not None and prof.storage_type == "s3":
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
    db = SessionLocal()
    try:
        seq = compute_enabled_server_capabilities(settings, db)
    finally:
        db.close()
    reply.server_capabilities[:] = seq
