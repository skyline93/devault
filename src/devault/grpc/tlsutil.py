"""TLS credential helpers for the embedded Agent gRPC server."""

from __future__ import annotations

import logging
from pathlib import Path

import grpc

from devault.settings import Settings

logger = logging.getLogger(__name__)


def build_server_credentials(settings: Settings) -> grpc.ServerCredentials | None:
    """Return TLS server credentials, or None to keep the port insecure (dev / mesh-only)."""
    cert_p = settings.grpc_server_tls_cert_path
    key_p = settings.grpc_server_tls_key_path
    if not cert_p and not key_p:
        return None
    if not cert_p or not key_p:
        raise ValueError(
            "grpc_server_tls_cert_path and grpc_server_tls_key_path must both be set for TLS"
        )

    cert = Path(cert_p).read_bytes()
    key = Path(key_p).read_bytes()
    client_ca: bytes | None = None
    require_client = False
    if settings.grpc_server_tls_client_ca_path:
        client_ca = Path(settings.grpc_server_tls_client_ca_path).read_bytes()
        require_client = True
        logger.info("gRPC server TLS with client certificate verification (mTLS) enabled")
    else:
        logger.info("gRPC server TLS enabled (no client CA)")

    return grpc.ssl_server_credentials(
        [(key, cert)],
        root_certificates=client_ca,
        require_client_authentication=require_client,
    )
