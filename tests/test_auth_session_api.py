"""GET /api/v1/auth/session (十五-01); DB access mocked so tests run without PostgreSQL."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from devault.api import deps
from devault.api.main import app
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


def test_auth_session_dev_open(
    client_no_real_db: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DEVAULT_API_TOKEN", raising=False)
    monkeypatch.delenv("DEVAULT_OIDC_ISSUER", raising=False)
    monkeypatch.delenv("DEVAULT_OIDC_AUDIENCE", raising=False)
    settings_mod.get_settings.cache_clear()
    r = client_no_real_db.get("/api/v1/auth/session")
    assert r.status_code == 200
    data = r.json()
    assert data["role"] == "admin"
    assert data["principal_label"] == "dev-open"
    assert data["allowed_tenant_ids"] is None


def test_auth_session_legacy_bearer(
    client_no_real_db: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEVAULT_API_TOKEN", "legacy-secret")
    monkeypatch.delenv("DEVAULT_OIDC_ISSUER", raising=False)
    monkeypatch.delenv("DEVAULT_OIDC_AUDIENCE", raising=False)
    settings_mod.get_settings.cache_clear()
    assert client_no_real_db.get("/api/v1/auth/session").status_code == 401
    r = client_no_real_db.get(
        "/api/v1/auth/session",
        headers={"Authorization": "Bearer legacy-secret"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["role"] == "admin"
    assert data["principal_label"] == "legacy-api-token"
    assert data["allowed_tenant_ids"] is None


def test_auth_session_invalid_bearer_forbidden(
    client_no_real_db: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEVAULT_API_TOKEN", "legacy-secret")
    settings_mod.get_settings.cache_clear()
    r = client_no_real_db.get(
        "/api/v1/auth/session",
        headers={"Authorization": "Bearer wrong"},
    )
    assert r.status_code == 403
