from __future__ import annotations

from enum import StrEnum


class JobKind(StrEnum):
    BACKUP = "backup"
    RESTORE = "restore"
    RESTORE_DRILL = "restore_drill"


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
