from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select


def test_ready_endpoint_returns_200(iam_database_url: str) -> None:
    """Requires Postgres with migrations applied (see iam/README.md)."""
    os.environ["IAM_DATABASE_URL"] = iam_database_url
    from devault_iam.api.main import create_app
    from devault_iam.db.session import reset_engine_for_tests
    from devault_iam.settings import clear_settings_cache

    clear_settings_cache()
    reset_engine_for_tests()

    with TestClient(create_app()) as client:
        r = client.get("/v1/ready")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ready"
    assert body["permissions"] >= 6


def test_seed_roles_and_permissions_exist(iam_database_url: str) -> None:
    os.environ["IAM_DATABASE_URL"] = iam_database_url
    from devault_iam.db.models import Permission, Role
    from devault_iam.db.session import SessionLocal, reset_engine_for_tests
    from devault_iam.settings import clear_settings_cache

    clear_settings_cache()
    reset_engine_for_tests()

    db = SessionLocal()
    try:
        n_perm = len(db.scalars(select(Permission)).all())
        assert n_perm >= 6
        ta = db.scalar(select(Role).where(Role.name == "tenant_admin", Role.tenant_id.is_(None)))
        assert ta is not None
    finally:
        db.close()
