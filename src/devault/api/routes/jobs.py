from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from devault.api.deps import get_db, verify_bearer
from devault.api.schemas import CreateBackupJobBody, CreateRestoreJobBody, EnqueueResponse, JobOut
from devault.db.models import Job
from devault.services import control as control_svc

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post(
    "/backup",
    dependencies=[Depends(verify_bearer)],
    response_model=EnqueueResponse,
    summary="Enqueue backup job",
)
def create_backup_job(body: CreateBackupJobBody, db: Session = Depends(get_db)) -> EnqueueResponse:
    job = control_svc.create_backup_job(db, body)
    return EnqueueResponse(job_id=job.id, status=job.status)


@router.post(
    "/restore",
    dependencies=[Depends(verify_bearer)],
    response_model=EnqueueResponse,
    summary="Enqueue restore job",
)
def create_restore_job(body: CreateRestoreJobBody, db: Session = Depends(get_db)) -> EnqueueResponse:
    job = control_svc.create_restore_job(db, body)
    return EnqueueResponse(job_id=job.id, status=job.status)


@router.post(
    "/{job_id}/cancel",
    dependencies=[Depends(verify_bearer)],
    response_model=JobOut,
    summary="Cancel job",
)
def cancel_job(job_id: uuid.UUID, db: Session = Depends(get_db)) -> Job:
    return control_svc.cancel_job(db, job_id)


@router.post(
    "/{job_id}/retry",
    dependencies=[Depends(verify_bearer)],
    response_model=EnqueueResponse,
    summary="Retry failed backup job",
)
def retry_job(job_id: uuid.UUID, db: Session = Depends(get_db)) -> EnqueueResponse:
    job = control_svc.retry_failed_backup_job(db, job_id)
    return EnqueueResponse(job_id=job.id, status=job.status)


@router.get(
    "/{job_id}",
    dependencies=[Depends(verify_bearer)],
    response_model=JobOut,
    summary="Get job by id",
)
def get_job(job_id: uuid.UUID, db: Session = Depends(get_db)) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@router.get(
    "",
    dependencies=[Depends(verify_bearer)],
    response_model=list[JobOut],
    summary="List jobs",
)
def list_jobs(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[Job]:
    stmt = select(Job).order_by(Job.id.desc()).limit(limit).offset(offset)
    return list(db.scalars(stmt).all())
