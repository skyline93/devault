from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

_FORBIDDEN_KEY_RE = re.compile(
    r"(password|secret|credential|token|private[_-]?key|access[_-]?key)",
    re.IGNORECASE,
)


def _reject_secret_like_keys(obj: Any, *, path: str = "$") -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str) and _FORBIDDEN_KEY_RE.search(k):
                raise ValueError(f"forbidden config key at {path}.{k}")
            _reject_secret_like_keys(v, path=f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _reject_secret_like_keys(v, path=f"{path}[{i}]")


class PgbackrestPhysicalBackupConfigV1(BaseModel):
    """Non-secret fields for pgBackRest; credentials must come from Agent env / mounts only."""

    model_config = ConfigDict(title="PgbackrestPhysicalBackupConfigV1")

    version: Literal[1] = Field(1, description="Config schema version; must be 1.")
    stanza: str = Field(..., min_length=1, max_length=256)
    pg_host: str = Field(..., min_length=1, max_length=1024)
    pg_port: int = Field(5432, ge=1, le=65535)
    pg_data_path: str = Field(
        ...,
        min_length=1,
        max_length=4096,
        description="PostgreSQL data directory path on the database host (pgBackRest pg*-path).",
    )
    pgbackrest_operation: Literal["backup", "expire"] = Field(
        "backup",
        description="Run pgbackrest backup (full/incr) or expire.",
    )
    backup_type: Literal["full", "incr"] | None = Field(
        None,
        description="Required when pgbackrest_operation is backup; ignored for expire.",
    )
    repo_s3_bucket: str | None = Field(default=None, max_length=1024)
    repo_s3_prefix: str | None = Field(default=None, max_length=1024)
    repo_s3_region: str | None = Field(default=None, max_length=64)
    repo_s3_endpoint: str | None = Field(
        default=None,
        max_length=2048,
        description="Optional S3-compatible endpoint URL (non-secret).",
    )
    repo_path: str | None = Field(
        default=None,
        max_length=4096,
        description="Optional local or NAS repo1-path when not using repo1-s3-bucket.",
    )

    @model_validator(mode="before")
    @classmethod
    def reject_secret_like_in_raw(cls, data: Any) -> Any:
        if isinstance(data, dict):
            _reject_secret_like_keys(dict(data))
        return data

    @model_validator(mode="after")
    def operation_and_repo(self) -> PgbackrestPhysicalBackupConfigV1:
        if self.pgbackrest_operation == "backup":
            if self.backup_type is None:
                raise ValueError("backup_type is required when pgbackrest_operation is backup")
        else:
            if self.backup_type is not None:
                raise ValueError("backup_type must be omitted when pgbackrest_operation is expire")
        has_s3 = bool(self.repo_s3_bucket and str(self.repo_s3_bucket).strip()) and bool(
            self.repo_s3_prefix is not None and str(self.repo_s3_prefix).strip() != ""
        )
        has_local = bool(self.repo_path and str(self.repo_path).strip())
        if not has_s3 and not has_local:
            raise ValueError("Set repo_s3_bucket and repo_s3_prefix for S3 repo, or repo_path for filesystem repo")
        return self
