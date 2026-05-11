from __future__ import annotations

import uuid

import jwt
import pytest
from fastapi.testclient import TestClient

from devault_iam.api.main import create_app
from devault_iam.db.session import SessionLocal, reset_engine_for_tests
from devault_iam.settings import clear_settings_cache, get_settings
from support_users import create_user_with_tenant_membership


@pytest.fixture
def client() -> TestClient:
    clear_settings_cache()
    reset_engine_for_tests()
    with TestClient(create_app()) as c:
        yield c


def _password() -> str:
    return "ValidPassword123"


def test_login_platform_and_tenant_user_jwks_me_refresh_logout(
    client: TestClient,
    iam_platform_credentials: tuple[str, str],
) -> None:
    plat_email, plat_pw = iam_platform_credentials

    rp = client.post("/v1/auth/login", json={"email": plat_email, "password": plat_pw})
    assert rp.status_code == 200, rp.text
    plat_body = rp.json()
    assert plat_body.get("tenant_id") is None
    plat_access = plat_body["access_token"]

    slug = f"p1-{uuid.uuid4().hex[:10]}"
    rt = client.post(
        "/v1/tenants",
        json={"name": "P1 Org", "slug": slug},
        headers={"Authorization": f"Bearer {plat_access}"},
    )
    assert rt.status_code == 201, rt.text
    new_tid = uuid.UUID(rt.json()["id"])

    db = SessionLocal()
    try:
        uemail = f"p1mem_{uuid.uuid4().hex[:12]}@example.com"
        create_user_with_tenant_membership(
            db,
            email=uemail,
            password_plain=_password(),
            tenant_id=new_tid,
            role_name="tenant_admin",
            display_name="P1 Member",
        )
    finally:
        db.close()

    r = client.post("/v1/auth/login", json={"email": uemail, "password": _password()})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("tenant_id")
    tid = uuid.UUID(str(body["tenant_id"]))
    assert tid == new_tid

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
    assert payload["tid"] == str(tid)
    assert "perm" in payload and len(payload["perm"]) >= 1

    rme = client.get("/v1/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert rme.status_code == 200
    me = rme.json()
    assert me["email"] == uemail
    assert str(tid) in me["tenant_ids"]

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
