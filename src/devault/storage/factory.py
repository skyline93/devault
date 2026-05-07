from __future__ import annotations

from pathlib import Path

from devault.settings import Settings, get_settings
from devault.storage.local import LocalStorage
from devault.storage.s3 import S3Storage
from devault.storage.types import Storage


def get_storage(settings: Settings | None = None) -> Storage:
    s = settings or get_settings()
    if s.storage_backend == "local":
        return LocalStorage(Path(s.local_storage_root))
    if s.storage_backend == "s3":
        if not s.s3_access_key or not s.s3_secret_key:
            raise RuntimeError("S3 storage requires DEVAULT_S3_ACCESS_KEY and DEVAULT_S3_SECRET_KEY")
        return S3Storage(
            endpoint_url=s.s3_endpoint,
            access_key=s.s3_access_key,
            secret_key=s.s3_secret_key,
            bucket=s.s3_bucket,
            region=s.s3_region,
            use_ssl=s.s3_use_ssl,
        )
    raise RuntimeError(f"Unknown storage backend: {s.storage_backend}")
