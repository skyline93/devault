from __future__ import annotations

import json
from pathlib import Path

from devault.plugins.file.multipart_resume import (
    manifest_encryption_matches_policy,
    validate_multipart_resume_checkpoint,
)


def test_manifest_encryption_matches_policy() -> None:
    m_plain = {"checksum_sha256": "a", "size_bytes": 1}
    m_enc = {"checksum_sha256": "b", "size_bytes": 2, "encryption": {"algorithm": "aes-256-gcm"}}
    assert manifest_encryption_matches_policy(m_plain, {}) is True
    assert manifest_encryption_matches_policy(m_plain, {"encrypt_artifacts": False}) is True
    assert manifest_encryption_matches_policy(m_plain, {"encrypt_artifacts": True}) is False
    assert manifest_encryption_matches_policy(m_enc, {"encrypt_artifacts": True}) is True
    assert manifest_encryption_matches_policy(m_enc, {}) is False


def test_validate_multipart_resume_ok(tmp_path: Path) -> None:
    wip = tmp_path / "bundle.tar.gz"
    wip.write_bytes(b"x" * 100)
    ck = {
        "upload_id": "u1",
        "content_length": 100,
        "checksum_sha256": "deadbeef",
        "manifest": {"encryption": {"algorithm": "aes-256-gcm"}, "size_bytes": 100},
    }
    ok, reason = validate_multipart_resume_checkpoint(
        wip_bundle=wip,
        checkpoint=ck,
        policy_config={"encrypt_artifacts": True},
    )
    assert ok is True
    assert reason == ""


def test_validate_multipart_resume_encryption_mismatch(tmp_path: Path) -> None:
    wip = tmp_path / "bundle.tar.gz"
    wip.write_bytes(b"x" * 10)
    ck = {
        "upload_id": "u1",
        "content_length": 10,
        "checksum_sha256": "ab",
        "manifest": {"size_bytes": 10},
    }
    ok, reason = validate_multipart_resume_checkpoint(
        wip_bundle=wip,
        checkpoint=ck,
        policy_config={"encrypt_artifacts": True},
    )
    assert ok is False
    assert reason == "manifest_encryption_mismatch"


def test_validate_multipart_resume_size_mismatch(tmp_path: Path) -> None:
    wip = tmp_path / "bundle.tar.gz"
    wip.write_bytes(b"abc")
    ck = {
        "upload_id": "u1",
        "content_length": 99,
        "checksum_sha256": "ab",
        "manifest": {"size_bytes": 99},
    }
    ok, reason = validate_multipart_resume_checkpoint(
        wip_bundle=wip,
        checkpoint=ck,
        policy_config={"encrypt_artifacts": False},
    )
    assert ok is False
    assert reason == "checkpoint_bundle_size_mismatch"


def test_write_multipart_checkpoint_includes_encrypt_flag(tmp_path: Path) -> None:
    from devault.plugins.file.plugin import write_multipart_checkpoint

    p = tmp_path / "ck.json"
    mf = {"size_bytes": 1, "encryption": {"algorithm": "aes-256-gcm"}}
    write_multipart_checkpoint(
        p,
        upload_id="uid",
        bundle_key="b",
        manifest_key="m",
        content_length=500,
        part_size=100,
        checksum_sha256="c0",
        manifest=mf,
        parts=[],
    )
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data.get("encrypt_artifacts") is True
