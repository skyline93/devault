"""AES-256-GCM chunked file encryption for large backup bundles."""

from __future__ import annotations

import base64
import hashlib
import os
import struct
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from devault.settings import Settings

# Magic + format version byte (v1).
MAGIC = b"DVENC\x01"
DEFAULT_CHUNK_SIZE = 64 * 1024 * 1024


class ArtifactCryptoError(Exception):
    """Invalid ciphertext, key, or format."""


def parse_aes256_key(raw: str) -> bytes:
    """Decode a standard Base64-encoded 32-byte AES-256 key."""
    s = raw.strip()
    if not s:
        raise ArtifactCryptoError("DEVAULT_ARTIFACT_ENCRYPTION_KEY is empty")
    try:
        key = base64.b64decode(s, validate=True)
    except Exception as e:
        raise ArtifactCryptoError(
            "DEVAULT_ARTIFACT_ENCRYPTION_KEY must be standard Base64 (32 raw bytes)"
        ) from e
    if len(key) != 32:
        raise ArtifactCryptoError(
            f"DEVAULT_ARTIFACT_ENCRYPTION_KEY must decode to 32 bytes, got {len(key)}"
        )
    return key


def parse_aes256_key_from_settings(settings: Settings) -> bytes | None:
    raw = settings.artifact_encryption_key
    if not raw:
        return None
    return parse_aes256_key(raw)


def encrypt_bundle_file(
    key: bytes,
    plaintext_path: Path,
    ciphertext_path: Path,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> tuple[int, str]:
    """Encrypt ``plaintext_path`` to ``ciphertext_path``. Returns (size_bytes, sha256_hex)."""
    aes = AESGCM(key)
    h = hashlib.sha256()
    total = 0
    ciphertext_path.parent.mkdir(parents=True, exist_ok=True)
    with plaintext_path.open("rb") as fin, ciphertext_path.open("wb") as fout:
        fout.write(MAGIC)
        h.update(MAGIC)
        total += len(MAGIC)
        idx = 0
        while True:
            block = fin.read(chunk_size)
            if not block:
                break
            nonce = os.urandom(12)
            ct = aes.encrypt(nonce, block, struct.pack(">Q", idx))
            chunk = nonce + struct.pack(">I", len(ct)) + ct
            fout.write(chunk)
            h.update(chunk)
            total += len(chunk)
            idx += 1
    return total, h.hexdigest()


def decrypt_bundle_file(
    key: bytes,
    ciphertext_path: Path,
    plaintext_path: Path,
) -> None:
    """Decrypt chunked AES-GCM bundle to ``plaintext_path``."""
    aes = AESGCM(key)
    plaintext_path.parent.mkdir(parents=True, exist_ok=True)
    with ciphertext_path.open("rb") as fin, plaintext_path.open("wb") as fout:
        magic = fin.read(len(MAGIC))
        if magic != MAGIC:
            raise ArtifactCryptoError("bundle does not start with DVENC magic")
        idx = 0
        while True:
            nonce = fin.read(12)
            if len(nonce) == 0:
                break
            if len(nonce) != 12:
                raise ArtifactCryptoError("truncated nonce")
            ln_b = fin.read(4)
            if len(ln_b) != 4:
                raise ArtifactCryptoError("truncated length prefix")
            ln = struct.unpack(">I", ln_b)[0]
            ct = fin.read(ln)
            if len(ct) != ln:
                raise ArtifactCryptoError("truncated ciphertext")
            pt = aes.decrypt(nonce, ct, struct.pack(">Q", idx))
            fout.write(pt)
            idx += 1
