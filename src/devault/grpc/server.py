from __future__ import annotations

import logging
from concurrent import futures

import grpc
from grpc_health.v1 import health, health_pb2, health_pb2_grpc

from devault.grpc.servicer import AgentControlServicer
from devault.grpc.tlsutil import build_server_credentials
from devault.grpc_gen import agent_pb2_grpc
from devault.settings import get_settings

logger = logging.getLogger(__name__)

_server: grpc.Server | None = None


def start_grpc_server() -> None:
    """Starts the Agent gRPC server in-process (control plane). No-op if grpc_listen is unset."""
    global _server
    settings = get_settings()
    if not settings.grpc_listen:
        return
    if _server is not None:
        return

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=16))
    agent_pb2_grpc.add_AgentControlServicer_to_server(AgentControlServicer(), server)

    health_servicer = health.HealthServicer()
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)
    health_servicer.set("", health_pb2.HealthCheckResponse.SERVING)
    health_servicer.set("devault.agent.v1.AgentControl", health_pb2.HealthCheckResponse.SERVING)

    creds = build_server_credentials(settings)
    if creds:
        bound = server.add_secure_port(settings.grpc_listen, creds)
        if bound == 0:
            raise RuntimeError(f"gRPC TLS: failed to bind {settings.grpc_listen!r}")
        logger.info("Agent gRPC listening with TLS on %s", settings.grpc_listen)
    else:
        bound = server.add_insecure_port(settings.grpc_listen)
        if bound == 0:
            raise RuntimeError(f"gRPC: failed to bind {settings.grpc_listen!r}")
        logger.warning(
            "Agent gRPC listening WITHOUT TLS on %s (set DEVAULT_GRPC_SERVER_TLS_* for encryption)",
            settings.grpc_listen,
        )

    server.start()
    _server = server


def stop_grpc_server() -> None:
    global _server
    if _server is not None:
        _server.stop(grace=5)
        _server = None
