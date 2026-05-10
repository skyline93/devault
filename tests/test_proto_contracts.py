"""Lightweight gRPC message contracts (no live server)."""

from __future__ import annotations

from devault.grpc_gen import agent_pb2


def test_heartbeat_reply_capabilities_roundtrip() -> None:
    m = agent_pb2.HeartbeatReply(
        ok=True,
        server_release="0.4.0",
        min_supported_agent_version="0.1.0",
        max_tested_agent_version="0.4.0",
        deprecation_message="",
        reason_code="",
        server_capabilities=["backup_file_v1", "multipart_upload"],
    )
    m2 = agent_pb2.HeartbeatReply()
    m2.ParseFromString(m.SerializeToString())
    assert list(m2.server_capabilities) == ["backup_file_v1", "multipart_upload"]


def test_heartbeat_request_snapshot_roundtrip() -> None:
    m = agent_pb2.HeartbeatRequest(
        agent_id="00000000-0000-4000-8000-000000000001",
        agent_release="0.4.0",
        proto_package="devault.agent.v1",
        git_commit="abc",
        hostname="edge-1",
        os="Linux 6.1",
        region="us-east-1",
        env="prod",
        backup_path_allowlist=["/data", "/var/backups"],
        snapshot_schema_version=1,
    )
    m2 = agent_pb2.HeartbeatRequest()
    m2.ParseFromString(m.SerializeToString())
    assert m2.snapshot_schema_version == 1
    assert m2.hostname == "edge-1"
    assert list(m2.backup_path_allowlist) == ["/data", "/var/backups"]


def test_complete_job_request_agent_hostname_roundtrip() -> None:
    m = agent_pb2.CompleteJobRequest(
        agent_id="00000000-0000-4000-8000-000000000001",
        job_id="00000000-0000-4000-8000-000000000002",
        success=True,
        agent_hostname="edge-a.example",
    )
    m2 = agent_pb2.CompleteJobRequest()
    m2.ParseFromString(m.SerializeToString())
    assert m2.agent_hostname == "edge-a.example"


def test_register_reply_capabilities_roundtrip() -> None:
    m = agent_pb2.RegisterReply(
        ok=True,
        bearer_token="x",
        expires_in_seconds=0,
        message="ok",
        server_release="0.4.0",
        min_supported_agent_version="0.1.0",
        max_tested_agent_version="0.4.0",
        deprecation_message="",
        reason_code="",
        server_capabilities=["agent_grpc_v1", "s3_presign_bundle"],
    )
    m2 = agent_pb2.RegisterReply()
    m2.ParseFromString(m.SerializeToString())
    assert "s3_presign_bundle" in m2.server_capabilities
