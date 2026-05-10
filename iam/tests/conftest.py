from __future__ import annotations

import os

import pytest


@pytest.fixture(scope="session")
def iam_database_url() -> str:
    return os.environ.get(
        "IAM_TEST_DATABASE_URL",
        "postgresql+psycopg://iam:iam@127.0.0.1:5433/iam",
    )


@pytest.fixture(scope="session", autouse=True)
def _configure_iam_env(iam_database_url: str) -> None:
    os.environ["IAM_DATABASE_URL"] = iam_database_url
    os.environ.setdefault("IAM_ENVIRONMENT", "development")
    from devault_iam.settings import clear_settings_cache

    clear_settings_cache()
