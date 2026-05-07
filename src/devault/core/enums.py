from __future__ import annotations

from enum import StrEnum


class JobKind(StrEnum):
    BACKUP = "backup"
    RESTORE = "restore"


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    UPLOADING = "uploading"
    VERIFYING = "verifying"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


class PluginName(StrEnum):
    FILE = "file"
