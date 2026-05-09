from __future__ import annotations

import base64
import json
import os
import uuid
from pathlib import Path

import pytest

from devault.crypto.chunked_aes_gcm import (
    ArtifactCryptoError,
    decrypt_bundle_file,
    encrypt_bundle_file,
    parse_aes256_key,
)
from devault.db.constants import DEFAULT_TENANT_UUID
from devault.db.models import Job
from devault.plugins.file import run_file_backup
from devault.plugins.file.plugin import finalize_bundle_with_optional_encryption
from devault.settings import Settings
from devault.storage.local import LocalStorage


def test_chunked_encrypt_decrypt_roundtrip(tmp_path: Path) -> None:
    key = os.urandom(32)
    plain = tmp_path / "plain.bin"
    cipher = tmp_path / "cipher.bin"
    out = tmp_path / "out.bin"
    plain.write_bytes(b"hello " * 10000)

    sz, digest = encrypt_bundle_file(key, plain, cipher)
    assert sz == cipher.stat().st_size
    assert len(digest) == 64

    decrypt_bundle_file(key, cipher, out)
    assert out.read_bytes() == plain.read_bytes()


def test_parse_aes256_key_accepts_standard_base64() -> None:
    key = os.urandom(32)
    raw = base64.b64encode(key).decode("ascii")
    assert parse_aes256_key(raw) == key


def test_parse_aes256_key_rejects_wrong_length() -> None:
    with pytest.raises(ArtifactCryptoError):
        parse_aes256_key(base64.b64encode(os.urandom(16)).decode("ascii"))


def test_finalize_encrypt_updates_manifest(tmp_path: Path) -> None:
    key_b64 = base64.b64encode(os.urandom(32)).decode("ascii")
    settings = Settings(
        env_name="test",
        storage_backend="local",
        local_storage_root=str(tmp_path / "store"),
        artifact_encryption_key=key_b64,
    )

    src = tmp_path / "src"
    src.mkdir()
    (src / "a.txt").write_text("x", encoding="utf-8")

    job = Job(
        id=uuid.uuid4(),
        tenant_id=DEFAULT_TENANT_UUID,
        kind="backup",
        plugin="file",
        status="pending",
        trigger="manual",
        config_snapshot={"version": 1, "paths": [str(src)], "excludes": [], "encrypt_artifacts": True},
    )

    from devault.plugins.file.plugin import _build_backup_tarball, artifact_object_keys

    bk, mk = artifact_object_keys(settings, job.id, job.tenant_id)
    tar_path, manifest, size_b, chk = _build_backup_tarball(
        job,
        settings,
        bundle_key=bk,
        manifest_key=mk,
    )
    inner_chk = chk
    enc_path, manifest2, sz2, chk2 = finalize_bundle_with_optional_encryption(
        job.config_snapshot or {},
        settings,
        tar_path,
        manifest,
    )
    assert manifest2["plaintext_checksum_sha256"] == inner_chk
    assert manifest2["checksum_sha256"] == chk2
    assert manifest2["size_bytes"] == sz2
    assert manifest2.get("encryption", {}).get("format") == "devault-chunked-v1"
    enc_path.unlink(missing_ok=True)


def test_run_file_backup_encrypted_local_storage(tmp_path: Path) -> None:
    key_b64 = base64.b64encode(os.urandom(32)).decode("ascii")
    settings = Settings(
        env_name="test",
        storage_backend="local",
        local_storage_root=str(tmp_path / "store"),
        artifact_encryption_key=key_b64,
    )
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
        config_snapshot={
            "version": 1,
            "paths": [str(src)],
            "excludes": [],
            "encrypt_artifacts": True,
        },
    )
    storage = LocalStorage(tmp_path / "store")
    outcome = run_file_backup(job=job, settings=settings, storage=storage)

    raw = storage.get_bytes(outcome.manifest_key)
    mf = json.loads(raw.decode("utf-8"))
    assert mf.get("encryption")
    assert mf["plaintext_checksum_sha256"] != mf["checksum_sha256"]
