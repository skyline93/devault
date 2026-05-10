from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException

from devault.security.auth_context import AuthContext


def test_auth_admin_all_tenants() -> None:
    a = AuthContext(role="admin", allowed_tenant_ids=None, principal_label="x")
    tid = uuid.uuid4()
    a.ensure_tenant_access(tid)
    a.ensure_can_write()
    a.ensure_admin()


def test_tenant_user_cannot_platform_admin() -> None:
    tid = uuid.uuid4()
    a = AuthContext(
        role="admin",
        allowed_tenant_ids=frozenset({tid}),
        principal_label="user:a@b.com",
        principal_kind="tenant_user",
    )
    with pytest.raises(HTTPException) as ei:
        a.ensure_admin()
    assert ei.value.status_code == 403


def test_auth_operator_scoped() -> None:
    tid = uuid.uuid4()
    a = AuthContext(role="operator", allowed_tenant_ids=frozenset({tid}), principal_label="op")
    a.ensure_tenant_access(tid)
    with pytest.raises(HTTPException):
        a.ensure_tenant_access(uuid.uuid4())


def test_auth_auditor_read_only() -> None:
    tid = uuid.uuid4()
    a = AuthContext(role="auditor", allowed_tenant_ids=frozenset({tid}), principal_label="aud")
    a.ensure_tenant_access(tid)
    with pytest.raises(HTTPException):
        a.ensure_can_write()
