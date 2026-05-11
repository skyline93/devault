from __future__ import annotations

import hashlib
import json
import os
import sys
import uuid
from pathlib import Path

import pytest

_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))


@pytest.fixture(scope="session")
def iam_platform_credentials(iam_database_url: str) -> tuple[str, str]:
    """Single platform-admin email/password for the session (bootstrap on fresh DB).

    Persists credentials under ``/tmp`` keyed by ``IAM_DATABASE_URL`` so later tests can log in
    after the first bootstrap. If the DB already has a platform admin but the file is missing,
    tests fail with an actionable message (reset DB or add the JSON file).
    """
    h = hashlib.sha256(iam_database_url.encode()).hexdigest()[:24]
    cred_path = Path(f"/tmp/devault_iam_plat_{h}.json")
    if cred_path.exists():
        data = json.loads(cred_path.read_text(encoding="utf-8"))
        return str(data["email"]), str(data["password"])

    from devault_iam.cli_admin import main
    from devault_iam.db.models import User
    from devault_iam.db.session import SessionLocal, reset_engine_for_tests
    from devault_iam.settings import clear_settings_cache
    from sqlalchemy import select

    os.environ["IAM_DATABASE_URL"] = iam_database_url
    clear_settings_cache()
    reset_engine_for_tests()
    db = SessionLocal()
    try:
        if db.scalar(select(User.id).where(User.is_platform_admin.is_(True))) is not None:
            env_email = os.environ.get("IAM_TEST_PLATFORM_EMAIL", "").strip()
            env_password = os.environ.get("IAM_TEST_PLATFORM_PASSWORD", "")
            if env_email and env_password:
                return env_email, env_password
            pytest.skip(
                "IAM test DB already has a platform admin but no credential cache file. "
                f"Set IAM_TEST_PLATFORM_EMAIL and IAM_TEST_PLATFORM_PASSWORD, or write {cred_path} "
                'as {"email":"...","password":"..."}, or use a fresh database (see iam/tests/conftest.py).'
            )
    finally:
        db.close()

    email = f"itestplat_{uuid.uuid4().hex[:16]}@example.com"
    password = "ValidPassword123"
    pw_file = cred_path.parent / f"iam_boot_pw_{uuid.uuid4().hex}.txt"
    pw_file.write_text(password, encoding="utf-8")
    try:
        rc = main(
            ["bootstrap", "create-platform-user", "--email", email, "--password-file", str(pw_file)],
        )
    finally:
        pw_file.unlink(missing_ok=True)
    if rc != 0:
        pytest.fail(f"iam-admin bootstrap failed with exit code {rc}")
    cred_path.write_text(json.dumps({"email": email, "password": password}), encoding="utf-8")
    return email, password


@pytest.fixture(scope="session")
def iam_database_url() -> str:
    return os.environ.get(
        "IAM_TEST_DATABASE_URL",
        "postgresql+psycopg://devault:devault@127.0.0.1:5432/devault",
    )


@pytest.fixture(scope="session", autouse=True)
def _configure_iam_env(iam_database_url: str) -> None:
    os.environ["IAM_DATABASE_URL"] = iam_database_url
    os.environ.setdefault("IAM_ENVIRONMENT", "development")
    from devault_iam.settings import clear_settings_cache

    clear_settings_cache()
