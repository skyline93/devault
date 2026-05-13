"""Encrypt/decrypt storage profile secrets using ``DEVAULT_STORAGE_CONFIG_MASTER_KEY`` (Fernet)."""

from __future__ import annotations

import os

from cryptography.fernet import Fernet, InvalidToken


def fernet_from_master_key() -> Fernet | None:
    raw = (os.environ.get("DEVAULT_STORAGE_CONFIG_MASTER_KEY") or "").strip()
    if not raw:
        return None
    key = raw.encode("utf-8")
    return Fernet(key)


def encrypt_optional(plaintext: str | None, fernet: Fernet) -> str | None:
    if plaintext is None or plaintext == "":
        return None
    return fernet.encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt_optional(token: str | None, fernet: Fernet) -> str | None:
    if token is None or not str(token).strip():
        return None
    try:
        return fernet.decrypt(str(token).strip().encode("ascii")).decode("utf-8")
    except InvalidToken as e:
        raise ValueError("invalid or corrupt encrypted storage secret") from e
