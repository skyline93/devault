from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from devault.settings import Settings, get_settings
from devault.storage.local import LocalStorage
from devault.storage.s3 import S3Storage
from devault.storage.s3_client import build_s3_client_for_tenant, effective_s3_bucket
from devault.storage.types import Storage

if TYPE_CHECKING:
    from devault.db.models import Tenant


def get_storage(settings: Settings | None = None) -> Storage:
    s = settings or get_settings()
    if s.storage_backend == "local":
        return LocalStorage(Path(s.local_storage_root))
    if s.storage_backend == "s3":
        return S3Storage(client=build_s3_client_for_tenant(s, None), bucket=effective_s3_bucket(s, None))
    raise RuntimeError(f"Unknown storage backend: {s.storage_backend}")


def get_storage_for_tenant(settings: Settings, tenant: "Tenant | None") -> Storage:
    """Resolve storage backend and tenant-scoped S3 bucket/credentials (BYOB)."""
    if settings.storage_backend == "local":
        return LocalStorage(Path(settings.local_storage_root))
    if settings.storage_backend == "s3":
        return S3Storage(
            client=build_s3_client_for_tenant(settings, tenant),
            bucket=effective_s3_bucket(settings, tenant),
        )
    raise RuntimeError(f"Unknown storage backend: {settings.storage_backend}")
