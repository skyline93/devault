"""PgBackRest policy config validation (PolicyCreate / Pydantic)."""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from devault.api.schemas import PolicyCreate


def _base_pg_dict(**overrides: object) -> dict:
    d = {
        "version": 1,
        "stanza": "main",
        "pg_host": "127.0.0.1",
        "pg_port": 5432,
        "pg_data_path": "/var/lib/postgresql/data",
        "pgbackrest_operation": "backup",
        "backup_type": "full",
        "repo_s3_bucket": "b",
        "repo_s3_prefix": "p/",
    }
    d.update(overrides)
    return d


def test_policy_create_pgbackrest_valid() -> None:
    aid = uuid.uuid4()
    p = PolicyCreate(
        name="pg",
        plugin="postgres_pgbackrest",
        config=_base_pg_dict(),
        bound_agent_id=aid,
    )
    assert p.plugin == "postgres_pgbackrest"


def test_policy_create_pgbackrest_expire_no_backup_type() -> None:
    aid = uuid.uuid4()
    cfg = _base_pg_dict(pgbackrest_operation="expire")
    del cfg["backup_type"]
    p = PolicyCreate(
        name="pg-expire",
        plugin="postgres_pgbackrest",
        config=cfg,
        bound_agent_id=aid,
    )
    assert p.config["pgbackrest_operation"] == "expire"


def test_policy_create_pgbackrest_rejects_secret_like_top_level_key() -> None:
    aid = uuid.uuid4()
    cfg = _base_pg_dict()
    cfg["repo_password"] = "x"
    with pytest.raises(ValidationError):
        PolicyCreate(
            name="bad",
            plugin="postgres_pgbackrest",
            config=cfg,
            bound_agent_id=aid,
        )


def test_policy_create_pgbackrest_backup_requires_backup_type() -> None:
    aid = uuid.uuid4()
    cfg = _base_pg_dict()
    del cfg["backup_type"]
    with pytest.raises(ValidationError):
        PolicyCreate(
            name="bad",
            plugin="postgres_pgbackrest",
            config=cfg,
            bound_agent_id=aid,
        )
