"""Edge agent registry and LeaseJobs enforcement (no live gRPC / DB)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import grpc
import pytest

from devault.db.models import EdgeAgent
from devault.grpc.agent_version import EXPECTED_PROTO_PACKAGE
from devault.services.edge_agents import enforce_edge_agent_for_lease
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


def test_enforce_aborts_when_row_missing() -> None:
    class _EmptyDb:
        def get(self, _model: type, _id: object) -> None:
            return None

    ctx = _FakeContext()
    s = Settings.model_construct(
        grpc_enforce_version_on_lease=True,
        grpc_min_supported_agent_version="0.1.0",
        grpc_max_tested_agent_version="",
        grpc_require_agent_version=False,
        grpc_upgrade_url=None,
    )
    with pytest.raises(_Abort):
        enforce_edge_agent_for_lease(
            _EmptyDb(),  # type: ignore[arg-type]
            agent_id=uuid.uuid4(),
            settings=s,
            context=ctx,  # type: ignore[arg-type]
            server_release="0.4.0",
        )
    assert ctx.code == grpc.StatusCode.FAILED_PRECONDITION


def test_enforce_skips_when_disabled() -> None:
    class _EmptyDb:
        def get(self, _model: type, _id: object) -> None:
            return None

    s = Settings.model_construct(
        grpc_enforce_version_on_lease=False,
    )
    enforce_edge_agent_for_lease(
        _EmptyDb(),  # type: ignore[arg-type]
        agent_id=uuid.uuid4(),
        settings=s,
        context=None,  # type: ignore[arg-type]
        server_release="0.4.0",
    )


def test_enforce_uses_stored_version() -> None:
    aid = uuid.uuid4()
    row = EdgeAgent(
        id=aid,
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
        agent_release="0.1.0",
        proto_package=EXPECTED_PROTO_PACKAGE,
        git_commit=None,
        last_register_at=None,
    )

    class _Db:
        def get(self, _model: type, id_: object) -> EdgeAgent | None:
            if id_ == aid:
                return row
            return None

    ctx = _FakeContext()
    s = Settings.model_construct(
        grpc_enforce_version_on_lease=True,
        grpc_min_supported_agent_version="1.0.0",
        grpc_max_tested_agent_version="",
        grpc_require_agent_version=False,
        grpc_upgrade_url=None,
    )
    with pytest.raises(_Abort):
        enforce_edge_agent_for_lease(
            _Db(),  # type: ignore[arg-type]
            agent_id=aid,
            settings=s,
            context=ctx,  # type: ignore[arg-type]
            server_release="1.0.0",
        )
