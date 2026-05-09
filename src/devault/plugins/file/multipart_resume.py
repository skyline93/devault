"""Multipart resume: local checkpoint must match policy (especially ``encrypt_artifacts`` vs manifest)."""

from __future__ import annotations

from pathlib import Path


def validate_multipart_resume_checkpoint(
    *,
    wip_bundle: Path,
    checkpoint: dict,
    policy_config: dict,
) -> tuple[bool, str]:
    """Return ``(True, "")`` if WIP bundle + checkpoint are safe to resume.

    ``reason`` when ``False`` is a stable machine-oriented code for logs/metrics.
    """
    if not isinstance(checkpoint, dict):
        return False, "checkpoint_not_object"
    manifest = checkpoint.get("manifest")
    if not isinstance(manifest, dict):
        return False, "manifest_missing_or_invalid"
    want_enc = bool(policy_config.get("encrypt_artifacts"))
    have_enc = bool(manifest.get("encryption"))
    if want_enc != have_enc:
        return False, "manifest_encryption_mismatch"
    try:
        expect_len = int(checkpoint.get("content_length", -1))
    except (TypeError, ValueError):
        return False, "content_length_invalid"
    if expect_len < 0:
        return False, "content_length_negative"
    if not wip_bundle.is_file():
        return False, "wip_bundle_missing"
    if wip_bundle.stat().st_size != expect_len:
        return False, "checkpoint_bundle_size_mismatch"
    return True, ""


def manifest_encryption_matches_policy(manifest: dict, policy_config: dict) -> bool:
    """Whether ``manifest`` encryption block presence matches ``encrypt_artifacts`` policy."""
    return bool(policy_config.get("encrypt_artifacts")) == bool(manifest.get("encryption"))
