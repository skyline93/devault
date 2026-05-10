"""§十六-12: SSO-only password login gate (unit-level)."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from devault.db.models import ConsoleUser, Tenant
from devault.services.sso_policy import console_user_password_login_blocked


def test_password_login_not_blocked_without_memberships() -> None:
    db = MagicMock()
    scalars_result = MagicMock()
    scalars_result.all.return_value = []
    db.scalars.return_value = scalars_result
    u = ConsoleUser(
        id=uuid.uuid4(),
        email="a@b.co",
        password_hash="x",
        disabled=False,
    )
    assert console_user_password_login_blocked(db, u) is False


def test_password_login_not_blocked_when_any_tenant_allows_password() -> None:
    tid_sso = uuid.uuid4()
    tid_open = uuid.uuid4()
    m1 = MagicMock(tenant_id=tid_sso)
    m2 = MagicMock(tenant_id=tid_open)
    db = MagicMock()
    scalars_result = MagicMock()
    scalars_result.all.return_value = [m1, m2]
    db.scalars.return_value = scalars_result

    t_sso = Tenant(
        id=tid_sso,
        name="T",
        slug="t",
        sso_password_login_disabled=True,
    )
    t_open = Tenant(
        id=tid_open,
        name="O",
        slug="o",
        sso_password_login_disabled=False,
    )

    def _get(_model: type, pk: uuid.UUID) -> Tenant | None:
        if pk == tid_sso:
            return t_sso
        if pk == tid_open:
            return t_open
        return None

    db.get.side_effect = lambda model, pk: _get(model, pk)
    u = ConsoleUser(
        id=uuid.uuid4(),
        email="a@b.co",
        password_hash="x",
        disabled=False,
    )
    assert console_user_password_login_blocked(db, u) is False


def test_password_login_blocked_when_all_tenants_sso_only() -> None:
    tid = uuid.uuid4()
    m = MagicMock()
    m.tenant_id = tid
    db = MagicMock()
    scalars_result = MagicMock()
    scalars_result.all.return_value = [m]
    db.scalars.return_value = scalars_result
    t = Tenant(
        id=tid,
        name="T",
        slug="t",
        sso_password_login_disabled=True,
    )
    db.get.return_value = t
    u = ConsoleUser(
        id=uuid.uuid4(),
        email="a@b.co",
        password_hash="x",
        disabled=False,
    )
    assert console_user_password_login_blocked(db, u) is True
