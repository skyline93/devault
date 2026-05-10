"""§十六-11: invitation accept rejects invalid tokens (no real DB)."""

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


def test_invitation_accept_invalid_token(
    client_no_real_db: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEVAULT_API_TOKEN", "secret-token")
    settings_mod.get_settings.cache_clear()
    r = client_no_real_db.post(
        "/api/v1/auth/invitations/accept",
        json={"token": "not-a-valid-invitation-token-xxxxxxxx"},
    )
    assert r.status_code == 400
