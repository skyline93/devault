#!/usr/bin/env python3
"""Minimal gRPC smoke: Register (bootstrap) + one Heartbeat against a running control plane."""

from __future__ import annotations

import os
import sys
import uuid

import grpc

from devault import __version__
from devault.grpc_gen import agent_pb2, agent_pb2_grpc


def _metadata(token: str) -> list[tuple[str, str]]:
    return [("authorization", f"Bearer {token}")]


def main() -> int:
    target = os.environ.get("DEVAULT_E2E_GRPC_TARGET", "127.0.0.1:50051").strip()
    secret = (
        os.environ.get("DEVAULT_E2E_REGISTRATION_SECRET")
        or os.environ.get("DEVAULT_GRPC_REGISTRATION_SECRET")
        or "devault-docker-register-secret"
    ).strip()
    if not target or not secret:
        print("error: DEVAULT_E2E_GRPC_TARGET and DEVAULT_E2E_REGISTRATION_SECRET required", file=sys.stderr)
        return 1

    # Must match a row in agent_enrollments (Compose / migration 0011 seeds the default below).
    agent_id = (
        os.environ.get("DEVAULT_E2E_AGENT_ID")
        or os.environ.get("DEVAULT_AGENT_ID")
        or "00000000-0000-4000-8000-000000000001"
    ).strip()
    ch = grpc.insecure_channel(target)
    try:
        stub = agent_pb2_grpc.AgentControlStub(ch)
        reg = stub.Register(
            agent_pb2.RegisterRequest(
                agent_id=agent_id,
                registration_secret=secret,
                agent_release=__version__,
                proto_package=agent_pb2.DESCRIPTOR.package,
                git_commit="e2e-smoke",
            ),
            metadata=[],
        )
        if not reg.ok or not reg.bearer_token:
            print("Register failed:", reg.message or "unknown", file=sys.stderr)
            return 2
        hb = stub.Heartbeat(
            agent_pb2.HeartbeatRequest(
                agent_id=agent_id,
                agent_release=__version__,
                proto_package=agent_pb2.DESCRIPTOR.package,
                git_commit="e2e-smoke",
            ),
            metadata=_metadata(reg.bearer_token),
        )
        if not hb.ok:
            print("Heartbeat not ok:", hb.reason_code or hb.deprecation_message or "unknown", file=sys.stderr)
            return 3
        print("ok: Register + Heartbeat", f"server_release={hb.server_release!r}")
        return 0
    finally:
        ch.close()


if __name__ == "__main__":
    raise SystemExit(main())
