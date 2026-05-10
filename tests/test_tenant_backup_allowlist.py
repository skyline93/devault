"""Tenant-scoped backup path allowlist union + policy path validation helpers."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from devault.db.models import AgentEnrollment, EdgeAgent, Tenant
from devault.services.tenant_backup_allowlist import (
    path_under_allowlist_prefix,
    union_backup_path_allowlist_for_tenant,
    validate_policy_paths_against_tenant_allowlist,
)


def test_path_under_allowlist_prefix() -> None:
    assert path_under_allowlist_prefix("/data/foo", "/data")
    assert path_under_allowlist_prefix("/data", "/data")
    assert not path_under_allowlist_prefix("/etc", "/data")


def test_union_and_enforce_rejects() -> None:
    tid = uuid.uuid4()
    aid = uuid.uuid4()
    t = Tenant(
        id=tid,
        name="Acme",
        slug="acme",
        policy_paths_allowlist_mode="enforce",
    )
    enr = AgentEnrollment(
        agent_id=aid,
        allowed_tenant_ids=[str(tid)],
    )
    edge = EdgeAgent(
        id=aid,
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
        backup_path_allowlist=["/data", "/var/w"],
    )

    class _Db:
        def get(self, model: type, pk: object) -> object | None:
            if model is Tenant and pk == tid:
                return t
            if model is EdgeAgent and pk == aid:
                return edge
            return None

        def scalars(self, _stmt: object):
            return self

        def all(self) -> list:
            return [enr]

    db = _Db()  # type: ignore[assignment]
    assert union_backup_path_allowlist_for_tenant(db, tid) == ["/data", "/var/w"]  # type: ignore[arg-type]

    with pytest.raises(HTTPException) as ei:
        validate_policy_paths_against_tenant_allowlist(db, tid, ["/etc/passwd"])  # type: ignore[arg-type]
    assert ei.value.status_code == 400


def test_warn_mode_logs_only(monkeypatch: pytest.MonkeyPatch) -> None:
    tid = uuid.uuid4()
    aid = uuid.uuid4()
    t = Tenant(
        id=tid,
        name="Acme",
        slug="acme2",
        policy_paths_allowlist_mode="warn",
    )
    enr = AgentEnrollment(
        agent_id=aid,
        allowed_tenant_ids=[str(tid)],
    )
    edge = EdgeAgent(
        id=aid,
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
        backup_path_allowlist=["/data"],
    )

    class _Db:
        def get(self, model: type, pk: object) -> object | None:
            if model is Tenant and pk == tid:
                return t
            if model is EdgeAgent and pk == aid:
                return edge
            return None

        def scalars(self, _stmt: object):
            return self

        def all(self) -> list:
            return [enr]

    db = _Db()  # type: ignore[assignment]
    validate_policy_paths_against_tenant_allowlist(db, tid, ["/etc"])  # type: ignore[arg-type] — should not raise
