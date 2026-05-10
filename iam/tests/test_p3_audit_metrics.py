from __future__ import annotations

import uuid

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from devault_iam.api.main import create_app
from devault_iam.db.models import AuditLog, TenantMember
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


def test_metrics_endpoint_exposes_prometheus(client: TestClient) -> None:
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "devault_iam_http" in r.text


def test_metrics_disabled_returns_404(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IAM_METRICS_ENABLED", "false")
    clear_settings_cache()
    reset_engine_for_tests()
    with TestClient(create_app()) as c:
        r = c.get("/metrics")
        assert r.status_code == 404


def test_register_writes_audit_log_and_platform_can_list(client: TestClient) -> None:
    email = f"p3_{uuid.uuid4().hex[:16]}@example.com"
    r = client.post(
        "/v1/auth/register",
        json={"email": email, "password": _password(), "name": "P3 User"},
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

    db = SessionLocal()
    try:
        cnt = db.scalar(
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.action == "auth.register", AuditLog.outcome == "success")
        )
        assert (cnt or 0) >= 1
    finally:
        db.close()

    lr = client.get(
        "/v1/platform/audit-logs",
        headers={"Authorization": f"Bearer {access}"},
        params={"action_prefix": "auth.register", "limit": 20},
    )
    assert lr.status_code == 200, lr.text
    rows = lr.json()
    assert any(x.get("action") == "auth.register" and x.get("outcome") == "success" for x in rows)


def test_response_includes_x_request_id_header(client: TestClient) -> None:
    r = client.get("/health", headers={"X-Request-Id": "my-correlation-1"})
    assert r.status_code == 200
    assert r.headers.get("x-request-id") == "my-correlation-1"
