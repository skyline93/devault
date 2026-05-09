from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TenantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Lowercase URL-safe identifier (e.g. acme-corp).",
    )

    @field_validator("slug")
    @classmethod
    def slug_normalized(cls, v: str) -> str:
        s = v.strip().lower()
        if not s.replace("-", "").replace("_", "").isalnum():
            raise ValueError("slug must be alphanumeric with optional hyphens/underscores")
        return s


class TenantOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    created_at: datetime
    require_encrypted_artifacts: bool = False
    kms_envelope_key_id: str | None = None
    s3_bucket: str | None = None
    s3_assume_role_arn: str | None = None
    s3_assume_role_external_id: str | None = None

    model_config = {"from_attributes": True}


class TenantPatch(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    require_encrypted_artifacts: bool | None = None
    kms_envelope_key_id: str | None = None
    s3_bucket: str | None = None
    s3_assume_role_arn: str | None = None
    s3_assume_role_external_id: str | None = None


class FileBackupConfigV1(BaseModel):
    """File-plugin backup configuration (version 1)."""

    model_config = ConfigDict(title="FileBackupConfigV1")

    version: Literal[1] = Field(1, description="Config schema version; must be 1.")
    paths: list[str] = Field(..., description="Absolute paths to back up (files or directories).")
    excludes: list[str] = Field(
        default_factory=list,
        description="Optional gitwildmatch patterns to exclude.",
    )
    follow_symlinks: bool = Field(False, description="Follow symlinks when walking paths (reserved).")
    preserve_uid_gid: bool = Field(True, description="Preserve uid/gid in archive metadata (reserved).")
    one_filesystem: bool = Field(False, description="Stay on one filesystem (reserved).")
    encrypt_artifacts: bool = Field(
        False,
        description="Encrypt backup bundle with AES-256-GCM before upload (KMS envelope or static key).",
    )
    kms_envelope_key_id: str | None = Field(
        default=None,
        description="KMS CMK id or ARN for envelope encryption (optional if tenant/platform default is set).",
    )
    object_lock_mode: Literal["GOVERNANCE", "COMPLIANCE"] | None = Field(
        default=None,
        description="S3 Object Lock mode when the bucket has Object Lock enabled.",
    )
    object_lock_retain_days: int | None = Field(
        default=None,
        ge=1,
        description="Object Lock retention window in days from upload time.",
    )
    retention_days: int | None = Field(
        default=None,
        ge=1,
        description="Optional retention: artifact eligible for automatic deletion this many days after successful backup.",
    )

    @model_validator(mode="after")
    def object_lock_pair(self) -> FileBackupConfigV1:
        if self.object_lock_mode is not None and self.object_lock_retain_days is None:
            raise ValueError("object_lock_retain_days is required when object_lock_mode is set")
        if self.object_lock_retain_days is not None and self.object_lock_mode is None:
            raise ValueError("object_lock_mode is required when object_lock_retain_days is set")
        return self


class CreateBackupJobBody(BaseModel):
    """Request body to enqueue a backup job."""

    plugin: Literal["file"] = Field("file", description="Backup plugin; only `file` is supported.")
    config: FileBackupConfigV1 | None = Field(
        None,
        description="Inline backup config when not referencing a saved policy.",
    )
    policy_id: uuid.UUID | None = Field(
        None,
        description="If set, use the saved policy config instead of inline `config`.",
    )
    idempotency_key: str | None = Field(
        None,
        description="Optional key; duplicate requests with the same key return the existing job.",
    )

    @field_validator("config", mode="before")
    @classmethod
    def ensure_config(cls, v: Any) -> Any:
        if v is None:
            return v
        if isinstance(v, dict) and "version" not in v:
            return {**v, "version": 1}
        return v

    @model_validator(mode="after")
    def policy_or_config(self) -> CreateBackupJobBody:
        if self.policy_id is None and self.config is None:
            raise ValueError("Either policy_id or config is required")
        return self


class CreateRestoreJobBody(BaseModel):
    """Request body to enqueue a restore job."""

    artifact_id: uuid.UUID = Field(..., description="Artifact UUID to restore from.")
    target_path: str = Field(
        ...,
        description="Absolute directory to extract into (must be allowed on the Agent).",
    )
    confirm_overwrite_non_empty: bool = Field(
        False,
        description="If true, allow restore when the target directory already has files.",
    )


class CreateRestoreDrillJobBody(BaseModel):
    """Manual automated restore drill: extract artifact under drill_base_path/devault-drill-<job_id>/."""

    artifact_id: uuid.UUID = Field(..., description="Artifact to verify by restoring on the Agent.")
    drill_base_path: str = Field(
        ...,
        description="Absolute directory prefix on the Agent (each run uses a unique devault-drill-<job_id>/ subfolder).",
    )


class JobOut(BaseModel):
    """Job row returned by the API."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    kind: str
    plugin: str
    status: str
    trigger: str
    policy_id: uuid.UUID | None = None
    config_snapshot: dict[str, Any]
    restore_artifact_id: uuid.UUID | None
    lease_agent_id: uuid.UUID | None = None
    lease_expires_at: datetime | None = None
    started_at: datetime | None
    finished_at: datetime | None
    error_code: str | None
    error_message: str | None
    trace_id: str | None
    result_meta: dict[str, Any] | None = Field(
        default=None,
        description="On successful restore_drill: JSON report echoed from the Agent (also written under extract_root).",
    )

    model_config = {"from_attributes": True}


class ArtifactOut(BaseModel):
    """Stored backup artifact metadata."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    job_id: uuid.UUID
    storage_backend: str
    bundle_key: str
    manifest_key: str
    size_bytes: int
    checksum_sha256: str
    compression: str
    encrypted: bool
    created_at: datetime
    retain_until: datetime | None = None
    legal_hold: bool = False

    model_config = {"from_attributes": True}


class ArtifactLegalHoldPatch(BaseModel):
    legal_hold: bool = Field(..., description="When true, retention purge skips this artifact.")


class EnqueueResponse(BaseModel):
    """Returned after enqueueing a backup or restore job."""

    job_id: uuid.UUID = Field(..., description="New or existing job id.")
    status: str = Field(..., description="Job status at enqueue time (often `pending`).")


class PolicyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Human-readable policy name.")
    plugin: Literal["file"] = Field("file", description="Plugin; only `file` is supported.")
    config: FileBackupConfigV1 = Field(..., description="Paths and exclude patterns.")
    enabled: bool = Field(True, description="Whether schedules and manual runs may use this policy.")


class PolicyPatch(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    config: FileBackupConfigV1 | None = None
    enabled: bool | None = None


class PolicyOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    plugin: str
    config: dict[str, Any]
    enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ScheduleCreate(BaseModel):
    policy_id: uuid.UUID = Field(..., description="Policy to run on this cron.")
    cron_expression: str = Field(
        ...,
        max_length=128,
        description="Five-field cron expression (APScheduler / croniter).",
    )
    timezone: str = Field("UTC", description="IANA time zone name for the cron.")
    enabled: bool = Field(True, description="Whether the scheduler should fire this schedule.")


class SchedulePatch(BaseModel):
    cron_expression: str | None = Field(None, max_length=128)
    timezone: str | None = None
    enabled: bool | None = None


class ScheduleOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    policy_id: uuid.UUID
    cron_expression: str
    timezone: str
    enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class RestoreDrillScheduleCreate(BaseModel):
    artifact_id: uuid.UUID = Field(..., description="Artifact whose recoverability is verified each run.")
    cron_expression: str = Field(
        ...,
        max_length=128,
        description="Five-field cron for devault-scheduler (same as backup schedules).",
    )
    timezone: str = Field("UTC", description="IANA time zone name.")
    enabled: bool = Field(True, description="Whether the scheduler should enqueue drills.")
    drill_base_path: str = Field(
        ...,
        description="Absolute path prefix on the Agent (runs extract into devault-drill-<job_id>/ below this path).",
    )


class RestoreDrillSchedulePatch(BaseModel):
    cron_expression: str | None = Field(None, max_length=128)
    timezone: str | None = None
    enabled: bool | None = None
    drill_base_path: str | None = None
    artifact_id: uuid.UUID | None = None


class RestoreDrillScheduleOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    artifact_id: uuid.UUID
    cron_expression: str
    timezone: str
    enabled: bool
    drill_base_path: str
    created_at: datetime

    model_config = {"from_attributes": True}


class EdgeAgentOut(BaseModel):
    """Registered edge Agent (from gRPC Heartbeat / Register)."""

    id: uuid.UUID = Field(..., description="Same as DEVAULT_AGENT_ID / Heartbeat agent_id.")
    first_seen_at: datetime
    last_seen_at: datetime
    agent_release: str | None = Field(None, description="Last reported SemVer string.")
    proto_package: str | None = Field(None, description="Last reported protobuf package (e.g. devault.agent.v1).")
    git_commit: str | None = Field(None, description="Optional Agent build SHA.")
    last_register_at: datetime | None = Field(None, description="Last successful Register RPC time, if any.")
    meets_min_supported_version: bool = Field(
        ...,
        description="True when agent_release parses as SemVer >= DEVAULT_GRPC_MIN_SUPPORTED_AGENT_VERSION.",
    )
    proto_matches_control_plane: bool = Field(
        ...,
        description="True when proto_package is empty or equals the control plane expected package.",
    )
