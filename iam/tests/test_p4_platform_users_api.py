from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from devault_iam.api.main import create_app
from devault_iam.db.models import TenantMember, User
from devault_iam.db.session import SessionLocal, reset_engine_for_tests
from devault_iam.security.passwords import hash_password
from devault_iam.services import permissions as perm_svc
from devault_iam.settings import clear_settings_cache

from support_users import create_user_with_tenant_membership


@pytest.fixture
def client() -> TestClient:
    clear_settings_cache()
    reset_engine_for_tests()
    with TestClient(create_app()) as c:
        yield c


def _pw() -> str:
    return "ValidPassword123"


def test_platform_users_crud_and_change_password_flow(
    client: TestClient,
    iam_platform_credentials: tuple[str, str],
) -> None:
    plat_email, plat_pw = iam_platform_credentials
    pr = client.post("/v1/auth/login", json={"email": plat_email, "password": plat_pw})
    assert pr.status_code == 200, pr.text
    plat_access = pr.json()["access_token"]

    nu = f"nu_{uuid.uuid4().hex[:12]}@example.com"
    cr = client.post(
        "/v1/platform/users",
        headers={"Authorization": f"Bearer {plat_access}"},
        json={"email": nu, "password": _pw(), "must_change_password": True},
    )
    assert cr.status_code == 201, cr.text
    assert cr.json()["must_change_password"] is True
    uid = cr.json()["id"]

    slug = f"p4pw-{uuid.uuid4().hex[:10]}"
    rt = client.post(
        "/v1/tenants",
        json={"name": "Pw Flow Org", "slug": slug},
        headers={"Authorization": f"Bearer {plat_access}"},
    )
    assert rt.status_code == 201, rt.text
    tid = rt.json()["id"]
    am = client.post(
        f"/v1/tenants/{tid}/members",
        headers={"Authorization": f"Bearer {plat_access}"},
        json={"email": nu, "role": "operator"},
    )
    assert am.status_code == 201, am.text

    lr = client.post("/v1/auth/login", json={"email": nu, "password": _pw()})
    assert lr.status_code == 200, lr.text
    assert lr.json().get("must_change_password") is True
    u_access = lr.json()["access_token"]

    bad = client.post(
        "/v1/auth/change-password",
        headers={"Authorization": f"Bearer {u_access}"},
        json={"current_password": "WrongPassword123", "new_password": "NewPassword4567"},
    )
    assert bad.status_code == 400

    ok = client.post(
        "/v1/auth/change-password",
        headers={"Authorization": f"Bearer {u_access}"},
        json={"current_password": _pw(), "new_password": "NewPassword4567"},
    )
    assert ok.status_code == 204

    lr2 = client.post("/v1/auth/login", json={"email": nu, "password": "NewPassword4567"})
    assert lr2.status_code == 200, lr2.text
    assert lr2.json().get("must_change_password") is False

    pa = client.patch(
        f"/v1/platform/users/{uid}",
        headers={"Authorization": f"Bearer {plat_access}"},
        json={"must_change_password": True},
    )
    assert pa.status_code == 200, pa.text
    assert pa.json()["must_change_password"] is True


def test_platform_users_rejects_tenant_bearer(
    client: TestClient,
    iam_platform_credentials: tuple[str, str],
) -> None:
    plat_email, plat_pw = iam_platform_credentials
    pr = client.post("/v1/auth/login", json={"email": plat_email, "password": plat_pw})
    plat_access = pr.json()["access_token"]
    slug = f"px-{uuid.uuid4().hex[:10]}"
    rt = client.post(
        "/v1/tenants",
        json={"name": "Px", "slug": slug},
        headers={"Authorization": f"Bearer {plat_access}"},
    )
    tid = uuid.UUID(rt.json()["id"])
    te = f"te_{uuid.uuid4().hex[:12]}@example.com"
    db = SessionLocal()
    try:
        create_user_with_tenant_membership(
            db,
            email=te,
            password_plain=_pw(),
            tenant_id=tid,
            role_name="tenant_admin",
        )
    finally:
        db.close()
    tr = client.post("/v1/auth/login", json={"email": te, "password": _pw()})
    t_access = tr.json()["access_token"]
    r = client.post(
        "/v1/platform/users",
        headers={"Authorization": f"Bearer {t_access}"},
        json={"email": f"x_{uuid.uuid4().hex[:8]}@example.com", "password": _pw()},
    )
    assert r.status_code == 403


def test_patch_member_rejects_platform_target_row(
    client: TestClient,
    iam_platform_credentials: tuple[str, str],
) -> None:
    """If a platform user incorrectly has a membership row, PATCH must reject."""
    plat_email, plat_pw = iam_platform_credentials
    pr = client.post("/v1/auth/login", json={"email": plat_email, "password": plat_pw})
    plat_access = pr.json()["access_token"]
    slug = f"pm-{uuid.uuid4().hex[:10]}"
    rt = client.post(
        "/v1/tenants",
        json={"name": "Pm", "slug": slug},
        headers={"Authorization": f"Bearer {plat_access}"},
    )
    tid = uuid.UUID(rt.json()["id"])
    admin_email = f"adm_{uuid.uuid4().hex[:12]}@example.com"
    db = SessionLocal()
    try:
        create_user_with_tenant_membership(
            db,
            email=admin_email,
            password_plain=_pw(),
            tenant_id=tid,
            role_name="tenant_admin",
        )
        role_op = perm_svc.get_template_role(db, "operator")
        assert role_op is not None
        p_user = User(
            email=f"pf_{uuid.uuid4().hex[:12]}@example.com",
            password_hash=hash_password(_pw()),
            name="pf",
            status="active",
            is_platform_admin=True,
        )
        db.add(p_user)
        db.flush()
        m_bad = TenantMember(tenant_id=tid, user_id=p_user.id, role_id=role_op.id, status="active")
        db.add(m_bad)
        db.commit()
        mid = m_bad.id
    finally:
        db.close()

    ar = client.post("/v1/auth/login", json={"email": admin_email, "password": _pw()})
    a_access = ar.json()["access_token"]
    pch = client.patch(
        f"/v1/tenants/{tid}/members/{mid}",
        headers={"Authorization": f"Bearer {a_access}"},
        json={"role": "auditor"},
    )
    assert pch.status_code == 400
    assert pch.json()["detail"] == "platform_user_cannot_join_tenant"

    de = client.delete(
        f"/v1/tenants/{tid}/members/{mid}",
        headers={"Authorization": f"Bearer {a_access}"},
    )
    assert de.status_code == 400
    assert de.json()["detail"] == "platform_user_cannot_join_tenant"
