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

from support_users import create_user_with_tenant_membership


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


def test_login_writes_audit_log_and_platform_can_list(
    client: TestClient,
    iam_platform_credentials: tuple[str, str],
) -> None:
    plat_email, plat_pw = iam_platform_credentials
    pr = client.post("/v1/auth/login", json={"email": plat_email, "password": plat_pw})
    assert pr.status_code == 200, pr.text
    plat_access = pr.json()["access_token"]
    slug = f"p3-{uuid.uuid4().hex[:10]}"
    rt = client.post(
        "/v1/tenants",
        json={"name": "P3 Org", "slug": slug},
        headers={"Authorization": f"Bearer {plat_access}"},
    )
    assert rt.status_code == 201, rt.text
    tid = uuid.UUID(rt.json()["id"])
    email = f"p3_{uuid.uuid4().hex[:16]}@example.com"
    db = SessionLocal()
    try:
        u = create_user_with_tenant_membership(
            db,
            email=email,
            password_plain=_password(),
            tenant_id=tid,
            role_name="operator",
            display_name="P3 User",
        )
        _promote_member_to_platform_admin(u.id, tid)
    finally:
        db.close()

    r = client.post("/v1/auth/login", json={"email": email, "password": _password()})
    assert r.status_code == 200, r.text
    body = r.json()
    access = body["access_token"]
    pub = client.app.state.jwt_public_pem
    payload = jwt.decode(
        access,
        pub,
        algorithms=["RS256"],
        audience=get_settings().jwt_audience,
        issuer=get_settings().jwt_issuer,
    )
    assert payload.get("tid")

    db = SessionLocal()
    try:
        cnt = db.scalar(
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.action == "auth.login", AuditLog.outcome == "success")
        )
        assert (cnt or 0) >= 1
    finally:
        db.close()

    lr = client.get(
        "/v1/platform/audit-logs",
        headers={"Authorization": f"Bearer {access}"},
        params={"action_prefix": "auth.login", "limit": 20},
    )
    assert lr.status_code == 200, lr.text
    rows = lr.json()
    assert any(x.get("action") == "auth.login" and x.get("outcome") == "success" for x in rows)


def test_response_includes_x_request_id_header(client: TestClient) -> None:
    r = client.get("/health", headers={"X-Request-Id": "my-correlation-1"})
    assert r.status_code == 200
    assert r.headers.get("x-request-id") == "my-correlation-1"
