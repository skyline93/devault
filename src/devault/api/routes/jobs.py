from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from devault.api.deps import get_db, get_effective_tenant, require_write
from devault.api.schemas import (
    CreateBackupJobBody,
    CreateRestoreDrillJobBody,
    CreateRestoreJobBody,
    EnqueueResponse,
    JobOut,
)
from devault.db.models import Job, Tenant
from devault.security.auth_context import AuthContext
from devault.services import control as control_svc

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/backup", response_model=EnqueueResponse, summary="Enqueue backup job")
def create_backup_job(
    body: CreateBackupJobBody,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant),
    _w: AuthContext = Depends(require_write),
) -> EnqueueResponse:
    job = control_svc.create_backup_job(db, body, tenant_id=tenant.id)
    return EnqueueResponse(job_id=job.id, status=job.status)


@router.post("/restore", response_model=EnqueueResponse, summary="Enqueue restore job")
def create_restore_job(
    body: CreateRestoreJobBody,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant),
    _w: AuthContext = Depends(require_write),
) -> EnqueueResponse:
    job = control_svc.create_restore_job(db, body, tenant_id=tenant.id)
    return EnqueueResponse(job_id=job.id, status=job.status)


@router.post("/restore-drill", response_model=EnqueueResponse, summary="Enqueue automated restore drill job")
def create_restore_drill_job(
    body: CreateRestoreDrillJobBody,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant),
    _w: AuthContext = Depends(require_write),
) -> EnqueueResponse:
    job = control_svc.create_restore_drill_job(db, body, tenant_id=tenant.id)
    return EnqueueResponse(job_id=job.id, status=job.status)


@router.post("/{job_id}/cancel", response_model=JobOut, summary="Cancel job")
def cancel_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant),
    _w: AuthContext = Depends(require_write),
) -> Job:
    return control_svc.cancel_job(db, job_id, tenant_id=tenant.id)


@router.post("/{job_id}/retry", response_model=EnqueueResponse, summary="Retry failed backup job")
def retry_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant),
    _w: AuthContext = Depends(require_write),
) -> EnqueueResponse:
    job = control_svc.retry_failed_backup_job(db, job_id, tenant_id=tenant.id)
    return EnqueueResponse(job_id=job.id, status=job.status)


@router.get("/{job_id}", response_model=JobOut, summary="Get job by id")
def get_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant),
) -> Job:
    job = db.get(Job, job_id)
    if job is None or job.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@router.get("", response_model=list[JobOut], summary="List jobs")
def list_jobs(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[Job]:
    stmt = (
        select(Job)
        .where(Job.tenant_id == tenant.id)
        .order_by(Job.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(stmt).all())
