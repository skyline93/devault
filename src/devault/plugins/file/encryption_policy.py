"""Encryption expectations for backup manifests (forced encryption, KMS envelope)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from devault.settings import Settings

if TYPE_CHECKING:
    from devault.db.models import Tenant


def encryption_required(settings: Settings, tenant: "Tenant | None") -> bool:
    if settings.require_encrypted_artifacts:
        return True
    if tenant is not None and tenant.require_encrypted_artifacts:
        return True
    return False


def manifest_declares_chunked_encryption(manifest: dict) -> bool:
    """True when manifest carries devault chunked ciphertext metadata."""
    enc = manifest.get("encryption")
    if not isinstance(enc, dict):
        return False
    if enc.get("algorithm") != "aes-256-gcm":
        return False
    if enc.get("format") != "devault-chunked-v1":
        return False
    return True
