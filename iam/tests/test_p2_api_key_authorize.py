from __future__ import annotations

import uuid

import jwt
import pytest
from fastapi.testclient import TestClient

from sqlalchemy import select

from devault_iam.api.main import create_app
from devault_iam.db.models import TenantMember
from devault_iam.db.session import SessionLocal, reset_engine_for_tests
from devault_iam.services import permissions as perm_svc
from devault_iam.settings import clear_settings_cache, get_settings


@pytest.fixture
def client() -> TestClient:
    clear_settings_cache()
    reset_engine_for_tests()
    with TestClient(create_app()) as c:
        yield c


def _password() -> str:
    return "ValidPassword123"


def _promote_member_to_platform_admin(user_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
    """Tests share a long-lived Postgres DB; new users are often `operator`, not platform_admin."""
    db = SessionLocal()
    try:
        role = perm_svc.get_template_role(db, "platform_admin")
        assert role is not None
        m = db.scalar(
            select(TenantMember).where(
                TenantMember.user_id == user_id,
                TenantMember.tenant_id == tenant_id,
                TenantMember.status == "active",
            )
        )
        assert m is not None
        m.role_id = role.id
        db.commit()
    finally:
        db.close()


def _register(client: TestClient) -> tuple[str, str, uuid.UUID, uuid.UUID]:
    email = f"p2_{uuid.uuid4().hex[:16]}@example.com"
    r = client.post(
        "/v1/auth/register",
        json={"email": email, "password": _password(), "name": "P2 User"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    access = body["access_token"]
    tid = uuid.UUID(body["tenant_id"])
    pub = client.app.state.jwt_public_pem
    payload = jwt.decode(
        access,
        pub,
        algorithms=["RS256"],
        audience=get_settings().jwt_audience,
        issuer=get_settings().jwt_issuer,
    )
    uid = uuid.UUID(str(payload["sub"]))
    _promote_member_to_platform_admin(uid, tid)
    return access, email, tid, uid


def test_api_key_token_decode_and_authorize(client: TestClient) -> None:
    access, _email, tid, _uid = _register(client)
    headers = {"Authorization": f"Bearer {access}"}

    cr = client.post(
        "/v1/platform/api-keys",
        headers=headers,
        json={"name": "p2-test", "scopes": ["devault.control.read"]},
    )
    assert cr.status_code == 201, cr.text
    created = cr.json()
    key_id = uuid.UUID(created["id"])
    secret = created["secret"]
    assert secret.startswith("dvk.")

    tr = client.post("/v1/auth/token", json={"grant_type": "api_key", "api_key": secret})
    assert tr.status_code == 200, tr.text
    tok = tr.json()
    assert tok["token_type"] == "bearer"
    assert tok["tenant_id"] is None
    assert "devault.control.read" in tok["permissions"]

    pub = client.app.state.jwt_public_pem
    ap_payload = jwt.decode(
        tok["access_token"],
        pub,
        algorithms=["RS256"],
        audience=get_settings().jwt_audience,
        issuer=get_settings().jwt_issuer,
    )
    assert ap_payload["sub"] == f"api_key:{key_id}"
    assert ap_payload.get("pk") == "api_key"
    assert "devault.control.read" in ap_payload.get("perm", [])

    ok = client.post(
        "/v1/authorize",
        json={
            "subject": {"type": "api_key", "id": str(key_id)},
            "tenant_id": str(tid),
            "action": "devault.control.read",
            "resource": None,
        },
    )
    assert ok.status_code == 200
    assert ok.json() == {"allowed": True}

    deny = client.post(
        "/v1/authorize",
        json={
            "subject": {"type": "api_key", "id": str(key_id)},
            "tenant_id": str(tid),
            "action": "devault.platform.admin",
            "resource": None,
        },
    )
    assert deny.status_code == 200
    assert deny.json() == {"allowed": False}


def test_authorize_internal_header_when_token_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IAM_INTERNAL_API_TOKEN", "internal-test-token")
    clear_settings_cache()
    reset_engine_for_tests()
    with TestClient(create_app()) as c:
        access, _email, tid, uid = _register(c)
        body = {
            "subject": {"type": "user", "id": str(uid)},
            "tenant_id": str(tid),
            "action": "devault.console.read",
            "resource": None,
        }
        r = c.post("/v1/authorize", json=body)
        assert r.status_code == 401
        assert r.json().get("detail") == "internal_token_required"

        r2 = c.post("/v1/authorize", json=body, headers={"X-Iam-Internal": "internal-test-token"})
        assert r2.status_code == 200
        assert r2.json().get("allowed") is True

        # Bearer on user routes still works
        me = c.get("/v1/me", headers={"Authorization": f"Bearer {access}"})
        assert me.status_code == 200


def test_api_key_disabled_rejects_token_exchange(client: TestClient) -> None:
    access, _email, tid, _uid = _register(client)
    headers = {"Authorization": f"Bearer {access}"}

    cr = client.post(
        "/v1/platform/api-keys",
        headers=headers,
        json={"name": "p2-disable", "scopes": ["devault.control.read"]},
    )
    assert cr.status_code == 201, cr.text
    key_id = cr.json()["id"]
    secret = cr.json()["secret"]

    patch = client.patch(f"/v1/api-keys/{key_id}", headers=headers, json={"enabled": False})
    assert patch.status_code == 200, patch.text

    tr = client.post("/v1/auth/token", json={"grant_type": "api_key", "api_key": secret})
    assert tr.status_code == 401

    # tenant-scoped key must not authorize outside its tenant
    t2 = client.post(
        "/v1/tenants",
        headers=headers,
        json={"name": "Other", "slug": f"other-{uuid.uuid4().hex[:8]}"},
    )
    assert t2.status_code == 201, t2.text
    other_tid = uuid.UUID(t2.json()["id"])

    cr2 = client.post(
        f"/v1/tenants/{tid}/api-keys",
        headers=headers,
        json={"name": "scoped", "scopes": ["devault.console.read"]},
    )
    assert cr2.status_code == 201, cr2.text
    sk = cr2.json()["secret"]
    kid2 = uuid.UUID(cr2.json()["id"])

    bad = client.post(
        "/v1/authorize",
        json={
            "subject": {"type": "api_key", "id": str(kid2)},
            "tenant_id": str(other_tid),
            "action": "devault.console.read",
            "resource": None,
        },
    )
    assert bad.status_code == 200
    assert bad.json() == {"allowed": False}
