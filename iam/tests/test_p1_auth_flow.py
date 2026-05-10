from __future__ import annotations

import uuid

import jwt
import pytest
from fastapi.testclient import TestClient

from devault_iam.api.main import create_app
from devault_iam.db.session import reset_engine_for_tests
from devault_iam.settings import clear_settings_cache, get_settings


@pytest.fixture
def client() -> TestClient:
    clear_settings_cache()
    reset_engine_for_tests()
    with TestClient(create_app()) as c:
        yield c


def _password() -> str:
    return "ValidPassword123"


def test_register_login_jwks_me_refresh_logout(client: TestClient) -> None:
    email = f"p1_{uuid.uuid4().hex[:16]}@example.com"
    pw = _password()
    r = client.post("/v1/auth/register", json={"email": email, "password": pw, "name": "P1 User"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert "access_token" in body and "refresh_token" in body
    assert body["token_type"] == "bearer"
    assert len(body["permissions"]) >= 1
    tid = body["tenant_id"]
    assert tid

    rj = client.get("/.well-known/jwks.json")
    assert rj.status_code == 200
    keys = rj.json()["keys"]
    assert len(keys) >= 1
    assert keys[0].get("kid") == get_settings().jwt_key_id

    pub_pem = client.app.state.jwt_public_pem
    payload = jwt.decode(
        body["access_token"],
        pub_pem,
        algorithms=["RS256"],
        audience=get_settings().jwt_audience,
        issuer=get_settings().jwt_issuer,
    )
    assert payload["sub"]
    assert payload["tid"] == tid
    assert "perm" in payload and len(payload["perm"]) >= 1

    rme = client.get("/v1/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert rme.status_code == 200
    me = rme.json()
    assert me["email"] == email
    assert tid in me["tenant_ids"]

    rr = client.post("/v1/auth/refresh", json={"refresh_token": body["refresh_token"]})
    assert rr.status_code == 200
    body2 = rr.json()
    assert body2["refresh_token"] != body["refresh_token"]
    assert body2["access_token"] != body["access_token"]

    lo = client.post("/v1/auth/logout", json={"refresh_token": body2["refresh_token"]})
    assert lo.status_code == 204

    rr2 = client.post("/v1/auth/refresh", json={"refresh_token": body2["refresh_token"]})
    assert rr2.status_code == 401


def test_mfa_enroll_start_requires_auth(client: TestClient) -> None:
    r = client.post("/v1/auth/mfa/enroll/start")
    assert r.status_code == 401
