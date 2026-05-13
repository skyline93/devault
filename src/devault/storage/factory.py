from __future__ import annotations

from pathlib import Path
import uuid

from sqlalchemy.orm import Session

from devault.db.models import StorageProfile
from devault.settings import Settings, get_settings
from devault.services.storage_profiles import require_active_profile, s3_conn_spec_from_profile
from devault.storage.local import LocalStorage
from devault.storage.s3 import S3Storage
from devault.storage.s3_client import build_s3_client_from_spec
from devault.storage.types import Storage


def _storage_from_profile_row(settings: Settings, profile: StorageProfile) -> Storage:
    if profile.storage_type == "local":
        root = profile.local_root or settings.local_storage_root
        return LocalStorage(Path(root).expanduser())
    if profile.storage_type == "s3":
        spec = s3_conn_spec_from_profile(profile, settings)
        return S3Storage(client=build_s3_client_from_spec(settings, spec), bucket=spec.bucket)
    raise ValueError(f"Unknown storage_type on profile: {profile.storage_type}")


def get_storage_for_artifact_row(
    db: Session, settings: Settings, *, storage_profile_id: uuid.UUID | None
) -> Storage:
    """Resolve storage for an artifact; NULL ``storage_profile_id`` uses the active profile (legacy rows)."""
    if storage_profile_id is None:
        return get_storage_for_active_profile(db, settings)
    return get_storage_for_profile(db, settings, storage_profile_id)


def get_storage_for_profile(db: Session, settings: Settings, profile_id: uuid.UUID) -> Storage:
    profile = db.get(StorageProfile, profile_id)
    if profile is None:
        raise ValueError("storage profile not found")
    return _storage_from_profile_row(settings, profile)


def get_storage_for_active_profile(db: Session, settings: Settings) -> Storage:
    return _storage_from_profile_row(settings, require_active_profile(db))


def get_storage(db: Session | None = None, settings: Settings | None = None) -> Storage:
    """Resolve storage for the active profile (requires DB session)."""
    if db is None:
        raise RuntimeError("get_storage requires a database session; use get_storage_for_active_profile(db, settings)")
    s = settings or get_settings()
    return get_storage_for_active_profile(db, s)


__all__ = [
    "Storage",
    "get_storage",
    "get_storage_for_active_profile",
    "get_storage_for_artifact_row",
    "get_storage_for_profile",
]
