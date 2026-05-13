"""Storage profiles REST: platform admin vs tenant JWT."""

from __future__ import annotations

import uuid
from collections.abc import Generator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from devault.api import deps
from devault.api.main import app
from devault.security.auth_context import AuthContext
import devault.settings as settings_mod


@pytest.fixture
def clear_settings_cache() -> Generator[None, None, None]:
    settings_mod.get_settings.cache_clear()
    yield
    settings_mod.get_settings.cache_clear()


@pytest.fixture
def client_no_real_db(clear_settings_cache: None) -> Generator[TestClient, None, None]:
    def _fake_db() -> Generator[MagicMock, None, None]:
        m = MagicMock()
        m.scalar.return_value = None
        yield m

    app.dependency_overrides[deps.get_db] = _fake_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _tenant_admin_ctx() -> AuthContext:
    tid = uuid.UUID("00000000-0000-4000-8000-000000000001")
    return AuthContext(
        role="admin",
        allowed_tenant_ids=frozenset({tid}),
        principal_label="tenant-admin",
        principal_kind="tenant_user",
        user_id=uuid.uuid4(),
    )


def test_storage_profiles_list_requires_platform_admin(
    client_no_real_db: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for k in (
        "DEVAULT_IAM_JWT_ISSUER",
        "DEVAULT_IAM_JWT_AUDIENCE",
        "DEVAULT_IAM_JWT_PUBLIC_KEY_PEM",
        "DEVAULT_IAM_JWKS_URL",
    ):
        monkeypatch.delenv(k, raising=False)
    settings_mod.get_settings.cache_clear()

    app.dependency_overrides[deps.get_auth_context] = _tenant_admin_ctx
    try:
        r = client_no_real_db.get(
            "/api/v1/storage-profiles",
            headers={"Authorization": "Bearer x", "X-DeVault-Tenant-Id": "00000000-0000-4000-8000-000000000001"},
        )
        assert r.status_code == 403
        assert r.json().get("detail") == "platform administrator required"
    finally:
        app.dependency_overrides.pop(deps.get_auth_context, None)


def test_storage_profiles_list_dev_open_ok(
    client_no_real_db: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for k in (
        "DEVAULT_IAM_JWT_ISSUER",
        "DEVAULT_IAM_JWT_AUDIENCE",
        "DEVAULT_IAM_JWT_PUBLIC_KEY_PEM",
        "DEVAULT_IAM_JWKS_URL",
    ):
        monkeypatch.delenv(k, raising=False)
    settings_mod.get_settings.cache_clear()

    r = client_no_real_db.get("/api/v1/storage-profiles")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
