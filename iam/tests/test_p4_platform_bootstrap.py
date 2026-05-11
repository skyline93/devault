from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from devault_iam.api.main import create_app
from devault_iam.db.models import User
from devault_iam.db.session import SessionLocal, reset_engine_for_tests
from devault_iam.security.passwords import hash_password
from devault_iam.services.platform_user_rules import ensure_user_may_receive_tenant_membership
from devault_iam.settings import clear_settings_cache

from support_users import create_user_with_tenant_membership


@pytest.fixture
def client() -> TestClient:
    clear_settings_cache()
    reset_engine_for_tests()
    with TestClient(create_app()) as c:
        yield c


def test_ensure_user_may_receive_tenant_membership_rejects_platform() -> None:
    u = User(
        email="p@example.com",
        password_hash="x",
        name="p",
        is_platform_admin=True,
    )
    with pytest.raises(ValueError, match="platform_user_cannot_join_tenant"):
        ensure_user_may_receive_tenant_membership(u)


def test_bootstrap_status_runs(iam_database_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IAM_DATABASE_URL", iam_database_url)
    from devault_iam.cli_admin import main

    clear_settings_cache()
    reset_engine_for_tests()
    code = main(["bootstrap", "status"])
    assert code == 0


def test_bootstrap_create_idempotent(iam_database_url: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("IAM_DATABASE_URL", iam_database_url)
    from devault_iam.cli_admin import main

    clear_settings_cache()
    reset_engine_for_tests()

    db = SessionLocal()
    try:
        if db.scalar(select(User.id).where(User.is_platform_admin.is_(True))) is not None:
            pytest.skip("IAM test DB already has a platform admin; cannot assert create path")
    finally:
        db.close()

    email = f"p4_boot_{uuid.uuid4().hex[:12]}@example.com"
    pw_file = tmp_path / "pw.txt"
    pw_file.write_text("ValidPassword123\n", encoding="utf-8")

    assert main(["bootstrap", "create-platform-user", "--email", email, "--password-file", str(pw_file)]) == 0
    assert main(["bootstrap", "create-platform-user", "--email", email, "--password-file", str(pw_file)]) != 0


def _password() -> str:
    return "ValidPassword123"


def test_add_member_rejects_platform_flag_user(
    client: TestClient,
    iam_platform_credentials: tuple[str, str],
) -> None:
    """Tenant admin cannot add a user marked ``is_platform_admin`` to a tenant."""
    plat_email, plat_pw = iam_platform_credentials
    pr = client.post("/v1/auth/login", json={"email": plat_email, "password": plat_pw})
    assert pr.status_code == 200, pr.text
    plat_access = pr.json()["access_token"]
    slug = f"p4-{uuid.uuid4().hex[:10]}"
    rt = client.post(
        "/v1/tenants",
        json={"name": "P4 Org", "slug": slug},
        headers={"Authorization": f"Bearer {plat_access}"},
    )
    assert rt.status_code == 201, rt.text
    tid = uuid.UUID(rt.json()["id"])
    email_member = f"p4m_{uuid.uuid4().hex[:12]}@example.com"
    db = SessionLocal()
    try:
        create_user_with_tenant_membership(
            db,
            email=email_member,
            password_plain=_password(),
            tenant_id=tid,
            role_name="tenant_admin",
            display_name="Member Admin",
        )
    finally:
        db.close()

    r = client.post("/v1/auth/login", json={"email": email_member, "password": _password()})
    assert r.status_code == 200, r.text
    access = r.json()["access_token"]

    db = SessionLocal()
    try:
        email_platform = f"p4p_{uuid.uuid4().hex[:12]}@example.com"
        db.add(
            User(
                email=email_platform,
                password_hash=hash_password(_password()),
                name="Platform",
                status="active",
                is_platform_admin=True,
            )
        )
        db.commit()
    finally:
        db.close()

    r2 = client.post(
        f"/v1/tenants/{tid}/members",
        headers={"Authorization": f"Bearer {access}"},
        json={"email": email_platform, "role": "operator"},
    )
    assert r2.status_code == 400, r2.text
    assert r2.json()["detail"] == "platform_user_cannot_join_tenant"
