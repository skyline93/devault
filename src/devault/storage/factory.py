from __future__ import annotations

from pathlib import Path

from devault.settings import Settings, get_settings
from devault.storage.local import LocalStorage
from devault.storage.s3 import S3Storage
from devault.storage.s3_client import build_s3_client
from devault.storage.types import Storage


def get_storage(settings: Settings | None = None) -> Storage:
    s = settings or get_settings()
    if s.storage_backend == "local":
        return LocalStorage(Path(s.local_storage_root))
    if s.storage_backend == "s3":
        return S3Storage(client=build_s3_client(s), bucket=s.s3_bucket)
    raise RuntimeError(f"Unknown storage backend: {s.storage_backend}")
