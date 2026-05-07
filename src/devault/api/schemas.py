from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class FileBackupConfigV1(BaseModel):
    version: Literal[1] = 1
    paths: list[str]
    excludes: list[str] = Field(default_factory=list)
    follow_symlinks: bool = False
    preserve_uid_gid: bool = True
    one_filesystem: bool = False


class CreateBackupJobBody(BaseModel):
    plugin: Literal["file"] = "file"
    config: FileBackupConfigV1
    idempotency_key: str | None = None

    @field_validator("config", mode="before")
    @classmethod
    def ensure_config(cls, v: Any) -> Any:
        if isinstance(v, dict) and "version" not in v:
            v = {**v, "version": 1}
        return v


class CreateRestoreJobBody(BaseModel):
    artifact_id: uuid.UUID
    target_path: str
    confirm_overwrite_non_empty: bool = False


class JobOut(BaseModel):
    id: uuid.UUID
    kind: str
    plugin: str
    status: str
    trigger: str
    config_snapshot: dict[str, Any]
    restore_artifact_id: uuid.UUID | None
    started_at: datetime | None
    finished_at: datetime | None
    error_code: str | None
    error_message: str | None
    trace_id: str | None

    model_config = {"from_attributes": True}


class ArtifactOut(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    storage_backend: str
    bundle_key: str
    manifest_key: str
    size_bytes: int
    checksum_sha256: str
    compression: str
    encrypted: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class EnqueueResponse(BaseModel):
    job_id: uuid.UUID
    status: str
