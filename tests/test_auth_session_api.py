"""GET /api/v1/auth/session — dev-open vs IAM JWT."""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
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


def _rsa_pem_pair() -> tuple[bytes, bytes]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return priv, pub


def test_auth_session_dev_open(
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
    r = client_no_real_db.get("/api/v1/auth/session")
    assert r.status_code == 200
    data = r.json()
    assert data["role"] == "admin"
    assert data["principal_label"] == "dev-open"
    assert data["allowed_tenant_ids"] is None
    assert data.get("principal_kind") == "platform"


def test_auth_session_iam_requires_bearer(
    client_no_real_db: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, pub = _rsa_pem_pair()
    monkeypatch.setenv("DEVAULT_IAM_JWT_ISSUER", "http://iam.test")
    monkeypatch.setenv("DEVAULT_IAM_JWT_AUDIENCE", "devault-api")
    monkeypatch.setenv("DEVAULT_IAM_JWT_PUBLIC_KEY_PEM", pub.decode())
    settings_mod.get_settings.cache_clear()
    assert client_no_real_db.get("/api/v1/auth/session").status_code == 401


def test_auth_session_iam_bearer_ok(
    client_no_real_db: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    priv, pub = _rsa_pem_pair()
    monkeypatch.setenv("DEVAULT_IAM_JWT_ISSUER", "http://iam.test")
    monkeypatch.setenv("DEVAULT_IAM_JWT_AUDIENCE", "devault-api")
    monkeypatch.setenv("DEVAULT_IAM_JWT_PUBLIC_KEY_PEM", pub.decode())
    settings_mod.get_settings.cache_clear()
    now = datetime.now(timezone.utc)
    tok = jwt.encode(
        {
            "sub": "00000000-0000-4000-8000-000000000099",
            "iss": "http://iam.test",
            "aud": "devault-api",
            "iat": now,
            "exp": now + timedelta(minutes=10),
            "perm": ["devault.platform.admin"],
            "pk": "platform",
            "mfa": True,
        },
        priv,
        algorithm="RS256",
        headers={"kid": "k1"},
    )
    r = client_no_real_db.get(
        "/api/v1/auth/session",
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["role"] == "admin"
    assert data.get("principal_kind") == "platform"
