"""Restore drill path resolution and schedule enqueue helpers."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from devault.core.enums import JobKind
from devault.plugins.file.plugin import (
    FileBackupError,
    _maybe_write_restore_drill_report,
    _require_restore_drill_workspace_clean,
    _resolve_restore_drill_paths,
    _restore_paths_and_target,
)
from devault.settings import Settings


def test_restore_drill_target_isolated_under_base() -> None:
    tid = uuid.uuid4()
    aid = uuid.uuid4()
    job = SimpleNamespace(
        id=uuid.uuid4(),
        kind=JobKind.RESTORE_DRILL.value,
        restore_artifact_id=aid,
        config_snapshot={
            "version": 1,
            "artifact_id": str(aid),
            "drill_base_path": "/restore/drills",
            "restore_drill": True,
        },
    )
    s = Settings(allowed_path_prefixes="/restore")
    a, target, confirm = _restore_paths_and_target(job, s)
    assert a == aid
    assert target.as_posix() == f"/restore/drills/devault-drill-{job.id}"
    assert confirm is True


def test_restore_drill_rejects_non_absolute_base() -> None:
    job = SimpleNamespace(
        id=uuid.uuid4(),
        kind=JobKind.RESTORE_DRILL.value,
        restore_artifact_id=uuid.uuid4(),
        config_snapshot={
            "artifact_id": str(uuid.uuid4()),
            "drill_base_path": "relative/path",
            "restore_drill": True,
        },
    )
    s = Settings()
    with pytest.raises(FileBackupError) as ei:
        _restore_paths_and_target(job, s)
    assert ei.value.code == "INVALID_CONFIG"


def test_resolve_restore_drill_paths_same_as_lease_target() -> None:
    aid = uuid.uuid4()
    jid = uuid.uuid4()
    job = SimpleNamespace(
        id=jid,
        kind=JobKind.RESTORE_DRILL.value,
        restore_artifact_id=aid,
        config_snapshot={
            "artifact_id": str(aid),
            "drill_base_path": "/restore/drills",
            "restore_drill": True,
        },
    )
    s = Settings(allowed_path_prefixes="/restore")
    a, target = _resolve_restore_drill_paths(job, s)
    assert a == aid
    assert target.as_posix() == f"/restore/drills/devault-drill-{jid}"


def test_require_restore_drill_workspace_clean_accepts_missing_dir(tmp_path) -> None:
    t = tmp_path / "devault-drill-x"
    _require_restore_drill_workspace_clean(t)


def test_require_restore_drill_workspace_clean_rejects_nonempty(tmp_path) -> None:
    t = tmp_path / "devault-drill-x"
    t.mkdir()
    (t / "stale.txt").write_text("x")
    with pytest.raises(FileBackupError) as ei:
        _require_restore_drill_workspace_clean(t)
    assert ei.value.code == "TARGET_NOT_EMPTY"


def test_maybe_write_drill_report_after_extract_nonempty(tmp_path) -> None:
    """Report step must not re-apply pre-extract emptiness check (regression)."""
    aid = uuid.uuid4()
    jid = uuid.uuid4()
    base = tmp_path / "drills"
    base.mkdir()
    target = base / f"devault-drill-{jid}"
    target.mkdir()
    (target / "hello.txt").write_text("from extract")
    job = SimpleNamespace(
        id=jid,
        kind=JobKind.RESTORE_DRILL.value,
        restore_artifact_id=aid,
        config_snapshot={
            "artifact_id": str(aid),
            "drill_base_path": str(base),
            "restore_drill": True,
        },
    )
    s = Settings(allowed_path_prefixes=str(tmp_path))
    rep = _maybe_write_restore_drill_report(
        job=job,
        settings=s,
        plaintext_manifest_checksum_sha256=None,
        agent_release="0.0.0-test",
    )
    assert rep is not None
    assert (target / ".devault-drill-report.json").is_file()
    raw = (target / ".devault-drill-report.json").read_text(encoding="utf-8")
    assert "devault-restore-drill-report-v1" in raw
    assert str(jid) in raw


def test_restore_drill_prefix_gate() -> None:
    job = SimpleNamespace(
        id=uuid.uuid4(),
        kind=JobKind.RESTORE_DRILL.value,
        restore_artifact_id=uuid.uuid4(),
        config_snapshot={
            "artifact_id": str(uuid.uuid4()),
            "drill_base_path": "/tmp/drills",
            "restore_drill": True,
        },
    )
    s = Settings(allowed_path_prefixes="/restore")
    with pytest.raises(FileBackupError) as ei:
        _restore_paths_and_target(job, s)
    assert ei.value.code == "PATH_NOT_ALLOWED"
