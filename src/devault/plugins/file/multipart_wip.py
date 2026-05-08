"""Agent-side layout for multipart bundle resume across process restarts."""

from __future__ import annotations

import shutil
from pathlib import Path

from devault.settings import Settings


def job_multipart_dir(settings: Settings, job_id: str) -> Path:
    return settings.agent_multipart_state_root / "multipart" / job_id


def bundle_wip_path(settings: Settings, job_id: str) -> Path:
    return job_multipart_dir(settings, job_id) / "bundle.tar.gz"


def checkpoint_path(settings: Settings, job_id: str) -> Path:
    return job_multipart_dir(settings, job_id) / "checkpoint.json"


def clear_job_multipart_state(settings: Settings, job_id: str) -> None:
    d = job_multipart_dir(settings, job_id)
    if d.is_dir():
        shutil.rmtree(d, ignore_errors=True)
