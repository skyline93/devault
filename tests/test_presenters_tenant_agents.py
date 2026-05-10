"""Regression: tenant_scoped_agents_for_tenant must return a list (never implicit None)."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from devault.api import presenters as presenters_mod
from devault.api.presenters import tenant_scoped_agents_for_tenant


def test_tenant_scoped_agents_returns_list_when_enrollments_exist(monkeypatch) -> None:
    tid = uuid.uuid4()
    aid = uuid.uuid4()

    def _ids(_db, _tenant_id: uuid.UUID) -> list[uuid.UUID]:
        return [aid]

    monkeypatch.setattr(presenters_mod, "list_enrolled_agent_ids_for_tenant", _ids)

    class _Enr:
        agent_id = aid
        allowed_tenant_ids = [str(tid)]

    db = MagicMock()
    chain = MagicMock()
    chain.all.return_value = [_Enr()]
    db.scalars.return_value = chain
    db.get.return_value = None

    out = tenant_scoped_agents_for_tenant(db, tid)
    assert isinstance(out, list)
    assert len(out) == 1
    assert out[0].id == aid
