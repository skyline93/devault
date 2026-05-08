from __future__ import annotations

import pytest
from pydantic import ValidationError

from devault.settings import Settings


def test_server_tls_cert_without_key_rejected() -> None:
    with pytest.raises(ValidationError, match="GRPC_SERVER_TLS"):
        Settings(
            grpc_server_tls_cert_path="/tmp/x.crt",
            grpc_server_tls_key_path=None,
        )


def test_client_mtls_paths_must_be_paired() -> None:
    with pytest.raises(ValidationError, match="TLS_CLIENT"):
        Settings(
            grpc_tls_client_cert_path="/tmp/c.crt",
            grpc_tls_client_key_path=None,
        )
