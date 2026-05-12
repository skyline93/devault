"""pgBackRest runner (mocked binary)."""

from __future__ import annotations

from pathlib import Path

import pytest

from devault.plugins.pgbackrest.runner import _write_pgbackrest_conf, run_pgbackrest_job


def _fake_pgbackrest_script(tmp_path: Path) -> Path:
    script = tmp_path / "fake_pgbackrest"
    script.write_text(
        """#!/bin/sh
set -e
# backup / expire main argv ends with operation word
case " $* " in
  *" info "*)
    echo '[{"name":"stub"}]'
    ;;
esac
exit 0
""",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return script


def test_run_pgbackrest_job_backup_mock(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    exe = _fake_pgbackrest_script(tmp_path)
    monkeypatch.setenv("DEVAULT_PGBACKREST_BIN", str(exe))
    out = run_pgbackrest_job(
        {
            "stanza": "demo",
            "pg_host": "h",
            "pg_port": 5432,
            "pg_data_path": "/data/pg",
            "pgbackrest_operation": "backup",
            "backup_type": "full",
            "repo_path": "/repo",
        },
        timeout_sec=30,
    )
    assert out["exit_code"] == 0
    assert out["stanza"] == "demo"
    assert out["pgbackrest_operation"] == "backup"
    assert "pgbackrest_info" in out


def test_run_pgbackrest_job_expire_mock(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    exe = _fake_pgbackrest_script(tmp_path)
    monkeypatch.setenv("DEVAULT_PGBACKREST_BIN", str(exe))
    out = run_pgbackrest_job(
        {
            "stanza": "demo",
            "pg_host": "h",
            "pg_port": 5432,
            "pg_data_path": "/data/pg",
            "pgbackrest_operation": "expire",
            "repo_path": "/repo",
        },
        timeout_sec=30,
    )
    assert out["exit_code"] == 0
    assert out["pgbackrest_operation"] == "expire"


def test_write_pgbackrest_conf_s3_http_sets_storage_verify_tls_off(tmp_path: Path) -> None:
    p = tmp_path / "pgbackrest.conf"
    _write_pgbackrest_conf(
        {
            "stanza": "s",
            "pg_host": "h",
            "pg_port": 5432,
            "pg_data_path": "/var/lib/postgresql/data",
            "repo_s3_bucket": "b",
            "repo_s3_prefix": "p/",
            "repo_s3_endpoint": "http://minio:9000",
        },
        path=p,
    )
    text = p.read_text(encoding="utf-8")
    assert "repo1-storage-verify-tls=n" in text
    assert "repo1-s3-endpoint=http://minio:9000" in text
    assert "repo1-path=/p" in text
    assert "repo1-s3-path-prefix" not in text
