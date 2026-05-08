from __future__ import annotations

import logging
from concurrent import futures

import grpc

from devault.grpc.servicer import AgentControlServicer
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
    server.add_insecure_port(settings.grpc_listen)
    server.start()
    _server = server
    logger.info("Agent gRPC listening on %s", settings.grpc_listen)


def stop_grpc_server() -> None:
    global _server
    if _server is not None:
        _server.stop(grace=5)
        _server = None
