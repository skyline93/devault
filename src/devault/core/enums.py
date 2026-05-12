from __future__ import annotations

from enum import StrEnum


class JobKind(StrEnum):
    BACKUP = "backup"
    RESTORE = "restore"
    RESTORE_DRILL = "restore_drill"
    # Agent-only: verify policy paths exist/readable; no artifact upload (§十四-11).
    PATH_PRECHECK = "path_precheck"


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    UPLOADING = "uploading"
    VERIFYING = "verifying"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class JobTrigger(StrEnum):
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    RETRY = "retry"


class PluginName(StrEnum):
    FILE = "file"
    POSTGRES_PGBACKREST = "postgres_pgbackrest"
