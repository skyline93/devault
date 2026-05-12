#!/usr/bin/env python3
"""Minimal gRPC smoke: Register + one Heartbeat with a tenant Agent token."""

from __future__ import annotations

import os
import sys

import grpc

from devault import __version__
from devault.grpc_gen import agent_pb2, agent_pb2_grpc


def _metadata(token: str) -> list[tuple[str, str]]:
    return [("authorization", f"Bearer {token}")]


def main() -> int:
    target = os.environ.get("DEVAULT_E2E_GRPC_TARGET", "127.0.0.1:50051").strip()
    bearer = (
        os.environ.get("DEVAULT_E2E_AGENT_TOKEN")
        or os.environ.get("DEVAULT_AGENT_TOKEN")
        or ""
    ).strip()
    if not target or not bearer:
        print("error: DEVAULT_E2E_GRPC_TARGET and DEVAULT_E2E_AGENT_TOKEN required", file=sys.stderr)
        return 1

    ch = grpc.insecure_channel(target)
    try:
        stub = agent_pb2_grpc.AgentControlStub(ch)
        md = _metadata(bearer)
        reg = stub.Register(
            agent_pb2.RegisterRequest(
                agent_release=__version__,
                proto_package=agent_pb2.DESCRIPTOR.package,
                git_commit="e2e-smoke",
                hostname="e2e-host",
                os="linux",
                snapshot_schema_version=1,
            ),
            metadata=md,
        )
        if not reg.ok or not (reg.agent_id or "").strip():
            print("Register failed:", reg.message or "unknown", file=sys.stderr)
            return 2
        agent_id = reg.agent_id.strip()
        hb = stub.Heartbeat(
            agent_pb2.HeartbeatRequest(
                agent_id=agent_id,
                agent_release=__version__,
                proto_package=agent_pb2.DESCRIPTOR.package,
                git_commit="e2e-smoke",
            ),
            metadata=md,
        )
        if not hb.ok:
            print("Heartbeat not ok:", hb.reason_code or hb.deprecation_message or "unknown", file=sys.stderr)
            return 3
        print("ok: Register + Heartbeat", f"agent_id={agent_id!r}", f"server_release={hb.server_release!r}")
        return 0
    finally:
        ch.close()


if __name__ == "__main__":
    raise SystemExit(main())
