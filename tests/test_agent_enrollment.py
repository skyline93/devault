"""Agent enrollment helpers and gRPC tenant gate."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import grpc
import pytest

from devault.grpc.servicer import _grpc_ensure_job_tenant, _pending_candidate_ids
from devault.security.auth_context import AuthContext
from devault.services.agent_enrollment import validate_tenant_ids_exist


def test_validate_tenant_ids_exist_empty_raises() -> None:
    db = MagicMock()
    with pytest.raises(ValueError, match="at least one"):
        validate_tenant_ids_exist(db, [])


def test_validate_tenant_ids_exist_missing() -> None:
    tid = uuid.uuid4()
    db = MagicMock()
    chain = MagicMock()
    chain.all.return_value = []
    db.scalars.return_value = chain
    with pytest.raises(ValueError, match="unknown tenant_id"):
        validate_tenant_ids_exist(db, [tid])


def test_grpc_ensure_job_tenant_denies() -> None:
    ctx = MagicMock()
    auth = AuthContext(
        role="operator",
        allowed_tenant_ids=frozenset({uuid.uuid4()}),
        principal_label="agent-session:x",
    )
    with pytest.raises(RuntimeError, match="unreachable"):
        _grpc_ensure_job_tenant(auth, uuid.uuid4(), ctx)
    ctx.abort.assert_called_once()
    assert ctx.abort.call_args[0][0] == grpc.StatusCode.PERMISSION_DENIED


def test_grpc_ensure_job_tenant_allows_none_scope() -> None:
    ctx = MagicMock()
    auth = AuthContext(role="admin", allowed_tenant_ids=None, principal_label="legacy")
    _grpc_ensure_job_tenant(auth, uuid.uuid4(), ctx)
    ctx.abort.assert_not_called()


def test_pending_candidate_ids_empty_scope_returns_empty() -> None:
    db = MagicMock()
    assert _pending_candidate_ids(db, frozenset(), uuid.uuid4()) == []
