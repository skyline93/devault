from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from devault.api.deps import get_db, get_effective_tenant, require_write
from devault.api.schemas import ScheduleCreate, ScheduleOut, SchedulePatch
from devault.db.models import Schedule, Tenant
from devault.security.auth_context import AuthContext
from devault.services import control as control_svc

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.post("", response_model=ScheduleOut, summary="Create schedule")
def create_schedule(
    body: ScheduleCreate,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant),
    _w: AuthContext = Depends(require_write),
) -> Schedule:
    return control_svc.create_schedule(db, body, tenant_id=tenant.id)


@router.get("", response_model=list[ScheduleOut], summary="List schedules")
def list_schedules(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant),
) -> list[Schedule]:
    stmt = select(Schedule).where(Schedule.tenant_id == tenant.id).order_by(Schedule.created_at.desc())
    return list(db.scalars(stmt).all())


@router.get("/{schedule_id}", response_model=ScheduleOut, summary="Get schedule")
def get_schedule(
    schedule_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant),
) -> Schedule:
    s = db.get(Schedule, schedule_id)
    if s is None or s.tenant_id != tenant.id:
        raise HTTPException(404, detail="schedule not found")
    return s


@router.patch("/{schedule_id}", response_model=ScheduleOut, summary="Update schedule")
def patch_schedule(
    schedule_id: uuid.UUID,
    body: SchedulePatch,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant),
    _w: AuthContext = Depends(require_write),
) -> Schedule:
    return control_svc.patch_schedule(db, schedule_id, body, tenant_id=tenant.id)


@router.delete("/{schedule_id}", summary="Delete schedule")
def delete_schedule(
    schedule_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant),
    _w: AuthContext = Depends(require_write),
) -> dict[str, str]:
    control_svc.delete_schedule(db, schedule_id, tenant_id=tenant.id)
    return {"status": "deleted"}
