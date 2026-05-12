"""Regression: tenant_scoped_agents_for_tenant must return a list (never implicit None)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

from devault.api import presenters as presenters_mod
from devault.api.presenters import tenant_scoped_agents_for_tenant


def test_tenant_scoped_agents_returns_list_when_registered_instances_exist(monkeypatch) -> None:
    tid = uuid.uuid4()
    aid = uuid.uuid4()

    def _ids(_db, _tenant_id: uuid.UUID) -> list[uuid.UUID]:
        return [aid]

    monkeypatch.setattr(presenters_mod, "list_registered_agent_ids_for_tenant", _ids)

    db = MagicMock()
    edge = MagicMock()
    edge.id = aid
    edge.agent_token_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    edge.first_seen_at = now
    edge.last_seen_at = now
    edge.agent_release = "0.4.0"
    edge.proto_package = "devault.agent.v1"
    edge.git_commit = None
    edge.last_register_at = None
    edge.hostname = "edge-1"
    edge.host_os = "Linux"
    edge.region = None
    edge.agent_env = None
    edge.backup_path_allowlist = None
    db.get.return_value = edge

    out = tenant_scoped_agents_for_tenant(db, tid)
    assert isinstance(out, list)
    assert len(out) == 1
    assert out[0].id == aid
