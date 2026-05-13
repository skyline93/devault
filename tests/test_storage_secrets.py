from __future__ import annotations

import pytest
from cryptography.fernet import Fernet

from devault.crypto.storage_secrets import decrypt_optional, encrypt_optional, fernet_from_master_key


@pytest.fixture
def master_key(monkeypatch: pytest.MonkeyPatch) -> str:
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("DEVAULT_STORAGE_CONFIG_MASTER_KEY", key)
    return key


def test_encrypt_decrypt_roundtrip(master_key: str) -> None:
    f = fernet_from_master_key()
    assert f is not None
    tok = encrypt_optional("secret-value", f)
    assert tok is not None
    assert decrypt_optional(tok, f) == "secret-value"


def test_fernet_missing_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEVAULT_STORAGE_CONFIG_MASTER_KEY", raising=False)
    assert fernet_from_master_key() is None
