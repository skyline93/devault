from __future__ import annotations

import uuid
from pathlib import Path

from devault.db.constants import DEFAULT_TENANT_UUID
from devault.db.models import Job
from devault.plugins.file import run_file_backup
from devault.settings import Settings
from devault.storage.local import LocalStorage


def test_run_file_backup_tar_gz_to_local_storage(tmp_path: Path) -> None:
    src = tmp_path / "src"
    (src / "nested").mkdir(parents=True)
    (src / "nested" / "f.txt").write_text("hello", encoding="utf-8")

    job = Job(
        id=uuid.uuid4(),
        tenant_id=DEFAULT_TENANT_UUID,
        kind="backup",
        plugin="file",
        status="pending",
        trigger="manual",
        config_snapshot={"version": 1, "paths": [str(src)], "excludes": []},
    )
    settings = Settings(
        env_name="test",
        storage_backend="local",
        local_storage_root=str(tmp_path / "store"),
    )
    storage = LocalStorage(tmp_path / "store")

    outcome = run_file_backup(job=job, settings=settings, storage=storage)

    assert outcome.size_bytes > 0
    assert len(outcome.checksum_sha256) == 64
    assert storage.exists(outcome.bundle_key)
    assert storage.exists(outcome.manifest_key)
    manifest = storage.get_bytes(outcome.manifest_key).decode("utf-8")
    assert '"plugin": "file"' in manifest
    assert '"devault_release":' in manifest
    assert '"grpc_proto_package":' in manifest
    assert "sources/0/nested/f.txt" in manifest
