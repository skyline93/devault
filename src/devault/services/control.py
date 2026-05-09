from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from devault.api.cronutil import validate_cron_expression
from devault.api.schemas import (
    CreateBackupJobBody,
    CreateRestoreJobBody,
    PolicyCreate,
    PolicyPatch,
    ScheduleCreate,
    SchedulePatch,
    TenantCreate,
)
from devault.core.enums import JobKind, JobStatus, JobTrigger, PluginName
from devault.core.locking import release_policy_job_lock
from devault.db.models import Artifact, Job, Policy, Schedule, Tenant
from devault.settings import get_settings


def create_tenant(db: Session, body: TenantCreate) -> Tenant:
    t = Tenant(name=body.name.strip(), slug=body.slug)
    db.add(t)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="tenant slug already exists") from None
    db.refresh(t)
    return t


def create_policy(db: Session, body: PolicyCreate, *, tenant_id: uuid.UUID) -> Policy:
    if body.plugin != "file":
        raise HTTPException(400, detail="Only plugin=file is supported")
    p = Policy(
        tenant_id=tenant_id,
        name=body.name,
        plugin=PluginName.FILE.value,
        config=body.config.model_dump(mode="json"),
        enabled=body.enabled,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def patch_policy(db: Session, policy_id: uuid.UUID, body: PolicyPatch, *, tenant_id: uuid.UUID) -> Policy:
    p = db.get(Policy, policy_id)
    if p is None or p.tenant_id != tenant_id:
        raise HTTPException(404, detail="policy not found")
    if body.name is not None:
        p.name = body.name
    if body.config is not None:
        p.config = body.config.model_dump(mode="json")
    if body.enabled is not None:
        p.enabled = body.enabled
    p.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(p)
    return p


def delete_policy(db: Session, policy_id: uuid.UUID, *, tenant_id: uuid.UUID) -> None:
    p = db.get(Policy, policy_id)
    if p is None or p.tenant_id != tenant_id:
        raise HTTPException(404, detail="policy not found")
    db.delete(p)
    db.commit()


def create_schedule(db: Session, body: ScheduleCreate, *, tenant_id: uuid.UUID) -> Schedule:
    pol = db.get(Policy, body.policy_id)
    if pol is None or pol.tenant_id != tenant_id:
        raise HTTPException(404, detail="policy not found")
    validate_cron_expression(body.cron_expression)
    s = Schedule(
        tenant_id=pol.tenant_id,
        policy_id=body.policy_id,
        cron_expression=body.cron_expression.strip(),
        timezone=body.timezone,
        enabled=body.enabled,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def patch_schedule(db: Session, schedule_id: uuid.UUID, body: SchedulePatch, *, tenant_id: uuid.UUID) -> Schedule:
    s = db.get(Schedule, schedule_id)
    if s is None or s.tenant_id != tenant_id:
        raise HTTPException(404, detail="schedule not found")
    if body.cron_expression is not None:
        validate_cron_expression(body.cron_expression)
        s.cron_expression = body.cron_expression.strip()
    if body.timezone is not None:
        s.timezone = body.timezone
    if body.enabled is not None:
        s.enabled = body.enabled
    db.commit()
    db.refresh(s)
    return s


def delete_schedule(db: Session, schedule_id: uuid.UUID, *, tenant_id: uuid.UUID) -> None:
    s = db.get(Schedule, schedule_id)
    if s is None or s.tenant_id != tenant_id:
        raise HTTPException(404, detail="schedule not found")
    db.delete(s)
    db.commit()


def create_backup_job(db: Session, body: CreateBackupJobBody, *, tenant_id: uuid.UUID) -> Job:
    if body.plugin != "file":
        raise HTTPException(status_code=400, detail="Only plugin=file is supported")

    policy_id: uuid.UUID | None = None
    if body.policy_id is not None:
        pol = db.get(Policy, body.policy_id)
        if pol is None or pol.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail="policy not found")
        if not pol.enabled:
            raise HTTPException(status_code=400, detail="policy is disabled")
        if pol.plugin != PluginName.FILE.value:
            raise HTTPException(status_code=400, detail="Unsupported policy plugin")
        snap = dict(pol.config)
        policy_id = pol.id
    else:
        assert body.config is not None
        snap = body.config.model_dump(mode="json")

    job = Job(
        tenant_id=tenant_id,
        kind=JobKind.BACKUP.value,
        plugin=PluginName.FILE.value,
        status=JobStatus.PENDING.value,
        trigger=JobTrigger.MANUAL.value,
        idempotency_key=body.idempotency_key,
        config_snapshot=snap,
        policy_id=policy_id,
    )
    db.add(job)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if body.idempotency_key:
            existing = db.scalar(
                select(Job).where(
                    Job.tenant_id == tenant_id,
                    Job.idempotency_key == body.idempotency_key,
                )
            )
            if existing is not None:
                return existing
        raise
    db.refresh(job)
    return job


def create_restore_job(db: Session, body: CreateRestoreJobBody, *, tenant_id: uuid.UUID) -> Job:
    art = db.get(Artifact, body.artifact_id)
    if art is None or art.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="artifact not found")

    target = Path(body.target_path)
    if not target.is_absolute():
        raise HTTPException(status_code=400, detail="target_path must be absolute")
    target = target.resolve(strict=False)
    if target.exists() and any(target.iterdir()) and not body.confirm_overwrite_non_empty:
        raise HTTPException(
            status_code=400,
            detail="target_path is not empty; set confirm_overwrite_non_empty=true to proceed",
        )

    cfg = {
        "version": 1,
        "artifact_id": str(body.artifact_id),
        "target_path": str(target),
        "confirm_overwrite_non_empty": body.confirm_overwrite_non_empty,
    }
    job = Job(
        tenant_id=tenant_id,
        kind=JobKind.RESTORE.value,
        plugin=PluginName.FILE.value,
        status=JobStatus.PENDING.value,
        trigger=JobTrigger.MANUAL.value,
        config_snapshot=cfg,
        restore_artifact_id=body.artifact_id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def cancel_job(db: Session, job_id: uuid.UUID, *, tenant_id: uuid.UUID) -> Job:
    job = db.get(Job, job_id)
    if job is None or job.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="job not found")
    terminal = {
        JobStatus.SUCCESS.value,
        JobStatus.FAILED.value,
        JobStatus.CANCELLED.value,
    }
    if job.status in terminal:
        raise HTTPException(status_code=400, detail="job already finished")
    settings = get_settings()
    if job.policy_id and job.status in (
        JobStatus.RUNNING.value,
        JobStatus.UPLOADING.value,
        JobStatus.VERIFYING.value,
    ):
        release_policy_job_lock(
            job.policy_id,
            job.id,
            redis_url=settings.redis_url,
        )
    job.lease_agent_id = None
    job.lease_expires_at = None
    job.status = JobStatus.CANCELLED.value
    job.error_code = "CANCELLED"
    job.error_message = "Cancelled by user"
    job.finished_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)
    return job


def retry_failed_backup_job(db: Session, job_id: uuid.UUID, *, tenant_id: uuid.UUID) -> Job:
    job = db.get(Job, job_id)
    if job is None or job.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="job not found")
    if job.status != JobStatus.FAILED.value:
        raise HTTPException(status_code=400, detail="only failed jobs can be retried")
    if job.kind != JobKind.BACKUP.value:
        raise HTTPException(status_code=400, detail="only backup jobs can be retried")

    new_job = Job(
        tenant_id=job.tenant_id,
        kind=JobKind.BACKUP.value,
        plugin=job.plugin,
        status=JobStatus.PENDING.value,
        trigger=JobTrigger.RETRY.value,
        policy_id=job.policy_id,
        config_snapshot=dict(job.config_snapshot),
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    return new_job
