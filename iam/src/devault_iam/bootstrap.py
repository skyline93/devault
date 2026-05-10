from __future__ import annotations

from pathlib import Path

from devault_iam.settings import Settings


def resolve_jwt_private_pem(settings: Settings) -> str:
    raw = (settings.jwt_private_key or "").strip()
    if raw:
        return raw
    path = (settings.jwt_private_key_file or "").strip()
    if path:
        return Path(path).read_text(encoding="utf-8")
    return ""


def resolve_jwt_public_pem(settings: Settings) -> str:
    raw = (settings.jwt_public_key or "").strip()
    if raw:
        return raw
    path = (settings.jwt_public_key_file or "").strip()
    if path:
        return Path(path).read_text(encoding="utf-8")
    return ""
