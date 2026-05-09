from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from devault.api.deps import get_db, get_effective_tenant, require_write
from devault.api.schemas import RestoreDrillScheduleCreate, RestoreDrillScheduleOut, RestoreDrillSchedulePatch
from devault.db.models import RestoreDrillSchedule, Tenant
from devault.security.auth_context import AuthContext
from devault.services import control as control_svc

router = APIRouter(prefix="/restore-drill-schedules", tags=["restore-drill-schedules"])


@router.post("", response_model=RestoreDrillScheduleOut, summary="Create restore-drill cron schedule")
def create_restore_drill_schedule(
    body: RestoreDrillScheduleCreate,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant),
    _w: AuthContext = Depends(require_write),
) -> RestoreDrillSchedule:
    return control_svc.create_restore_drill_schedule(db, body, tenant_id=tenant.id)


@router.get("", response_model=list[RestoreDrillScheduleOut], summary="List restore-drill schedules")
def list_restore_drill_schedules(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant),
) -> list[RestoreDrillSchedule]:
    stmt = (
        select(RestoreDrillSchedule)
        .where(RestoreDrillSchedule.tenant_id == tenant.id)
        .order_by(RestoreDrillSchedule.created_at.desc())
    )
    return list(db.scalars(stmt).all())


@router.get("/{schedule_id}", response_model=RestoreDrillScheduleOut, summary="Get restore-drill schedule")
def get_restore_drill_schedule(
    schedule_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant),
) -> RestoreDrillSchedule:
    s = db.get(RestoreDrillSchedule, schedule_id)
    if s is None or s.tenant_id != tenant.id:
        raise HTTPException(404, detail="restore drill schedule not found")
    return s


@router.patch("/{schedule_id}", response_model=RestoreDrillScheduleOut, summary="Update restore-drill schedule")
def patch_restore_drill_schedule(
    schedule_id: uuid.UUID,
    body: RestoreDrillSchedulePatch,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant),
    _w: AuthContext = Depends(require_write),
) -> RestoreDrillSchedule:
    return control_svc.patch_restore_drill_schedule(db, schedule_id, body, tenant_id=tenant.id)


@router.delete("/{schedule_id}", summary="Delete restore-drill schedule")
def delete_restore_drill_schedule(
    schedule_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant),
    _w: AuthContext = Depends(require_write),
) -> dict[str, str]:
    control_svc.delete_restore_drill_schedule(db, schedule_id, tenant_id=tenant.id)
    return {"status": "deleted"}
