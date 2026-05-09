"""Unit tests for gRPC Agent vs control plane version gate (no live gRPC server)."""

from __future__ import annotations

import grpc
import pytest

from devault.grpc.agent_version import (
    EXPECTED_PROTO_PACKAGE,
    evaluate_agent_version_gate,
)
from devault.settings import Settings


class _Abort(Exception):
    pass


class _FakeContext:
    def set_trailing_metadata(self, _md: tuple) -> None:
        pass

    def abort(self, code: grpc.StatusCode, details: str) -> None:
        self.code = code
        self.details = details
        raise _Abort()


def test_compatible_returns_empty_deprecation() -> None:
    ctx = _FakeContext()
    s = Settings.model_construct(
        grpc_min_supported_agent_version="0.1.0",
        grpc_max_tested_agent_version="",
        grpc_require_agent_version=False,
        grpc_upgrade_url=None,
    )
    dep = evaluate_agent_version_gate(
        agent_release="0.4.0",
        proto_package=EXPECTED_PROTO_PACKAGE,
        settings=s,
        context=ctx,  # type: ignore[arg-type]
        server_release="0.4.0",
    )
    assert dep == ""


def test_too_old_aborts() -> None:
    ctx = _FakeContext()
    s = Settings.model_construct(
        grpc_min_supported_agent_version="1.0.0",
        grpc_max_tested_agent_version="",
        grpc_require_agent_version=False,
        grpc_upgrade_url=None,
    )
    with pytest.raises(_Abort):
        evaluate_agent_version_gate(
            agent_release="0.4.0",
            proto_package=EXPECTED_PROTO_PACKAGE,
            settings=s,
            context=ctx,  # type: ignore[arg-type]
            server_release="1.0.0",
        )
    assert ctx.code == grpc.StatusCode.FAILED_PRECONDITION


def test_proto_mismatch_aborts() -> None:
    ctx = _FakeContext()
    s = Settings.model_construct(
        grpc_min_supported_agent_version="0.1.0",
        grpc_max_tested_agent_version="",
        grpc_require_agent_version=False,
        grpc_upgrade_url=None,
    )
    with pytest.raises(_Abort):
        evaluate_agent_version_gate(
            agent_release="0.4.0",
            proto_package="devault.agent.v2",
            settings=s,
            context=ctx,  # type: ignore[arg-type]
            server_release="0.4.0",
        )


def test_newer_than_max_tested_deprecation() -> None:
    ctx = _FakeContext()
    s = Settings.model_construct(
        grpc_min_supported_agent_version="0.1.0",
        grpc_max_tested_agent_version="0.4.0",
        grpc_require_agent_version=False,
        grpc_upgrade_url=None,
    )
    dep = evaluate_agent_version_gate(
        agent_release="9.0.0",
        proto_package=EXPECTED_PROTO_PACKAGE,
        settings=s,
        context=ctx,  # type: ignore[arg-type]
        server_release="0.4.0",
    )
    assert "newer" in dep.lower()


def test_legacy_missing_release_soft_warning() -> None:
    ctx = _FakeContext()
    s = Settings.model_construct(
        grpc_min_supported_agent_version="99.0.0",
        grpc_max_tested_agent_version="",
        grpc_require_agent_version=False,
        grpc_upgrade_url=None,
    )
    dep = evaluate_agent_version_gate(
        agent_release="",
        proto_package="",
        settings=s,
        context=ctx,  # type: ignore[arg-type]
        server_release="0.4.0",
    )
    assert dep


def test_require_release_aborts_when_empty() -> None:
    ctx = _FakeContext()
    s = Settings.model_construct(
        grpc_min_supported_agent_version="0.1.0",
        grpc_max_tested_agent_version="",
        grpc_require_agent_version=True,
        grpc_upgrade_url=None,
    )
    with pytest.raises(_Abort):
        evaluate_agent_version_gate(
            agent_release="",
            proto_package="",
            settings=s,
            context=ctx,  # type: ignore[arg-type]
            server_release="0.4.0",
        )
