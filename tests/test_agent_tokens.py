"""Agent token helpers and gRPC tenant gate."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import grpc
import pytest

from devault.grpc.servicer import _grpc_ensure_job_tenant, _pending_candidate_ids
from devault.security.auth_context import AuthContext
from devault.services.agent_tokens import hash_agent_token, mint_agent_token_secret


def test_hash_agent_token_stable() -> None:
    secret = mint_agent_token_secret()
    assert hash_agent_token(secret) == hash_agent_token(secret)


def test_grpc_ensure_job_tenant_denies() -> None:
    ctx = MagicMock()
    auth = AuthContext(
        role="operator",
        allowed_tenant_ids=frozenset({uuid.uuid4()}),
        principal_label="agent-token:x",
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
