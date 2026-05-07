from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from devault.api.deps import get_db, verify_bearer
from devault.api.schemas import CreateBackupJobBody, CreateRestoreJobBody, EnqueueResponse, JobOut
from devault.core.enums import JobKind, JobStatus, PluginName
from devault.db.models import Artifact, Job
from devault.worker.tasks import run_backup_job, run_restore_job

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/backup", dependencies=[Depends(verify_bearer)], response_model=EnqueueResponse)
def create_backup_job(body: CreateBackupJobBody, db: Session = Depends(get_db)) -> EnqueueResponse:
    if body.plugin != "file":
        raise HTTPException(status_code=400, detail="Only plugin=file is supported")
    snap = body.config.model_dump(mode="json")
    job = Job(
        kind=JobKind.BACKUP.value,
        plugin=PluginName.FILE.value,
        status=JobStatus.PENDING.value,
        trigger="manual",
        idempotency_key=body.idempotency_key,
        config_snapshot=snap,
    )
    db.add(job)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if body.idempotency_key:
            existing = db.scalar(select(Job).where(Job.idempotency_key == body.idempotency_key))
            if existing is not None:
                if existing.status == JobStatus.PENDING.value:
                    run_backup_job.delay(str(existing.id))
                return EnqueueResponse(job_id=existing.id, status=existing.status)
        raise
    db.refresh(job)
    run_backup_job.delay(str(job.id))
    return EnqueueResponse(job_id=job.id, status=job.status)


@router.post("/restore", dependencies=[Depends(verify_bearer)], response_model=EnqueueResponse)
def create_restore_job(body: CreateRestoreJobBody, db: Session = Depends(get_db)) -> EnqueueResponse:
    art = db.get(Artifact, body.artifact_id)
    if art is None:
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
        kind=JobKind.RESTORE.value,
        plugin=PluginName.FILE.value,
        status=JobStatus.PENDING.value,
        trigger="manual",
        config_snapshot=cfg,
        restore_artifact_id=body.artifact_id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    run_restore_job.delay(str(job.id))
    return EnqueueResponse(job_id=job.id, status=job.status)


@router.get("/{job_id}", dependencies=[Depends(verify_bearer)], response_model=JobOut)
def get_job(job_id: uuid.UUID, db: Session = Depends(get_db)) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@router.get("", dependencies=[Depends(verify_bearer)], response_model=list[JobOut])
def list_jobs(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[Job]:
    stmt = select(Job).order_by(Job.id.desc()).limit(limit).offset(offset)
    return list(db.scalars(stmt).all())
