from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from devault.api.deps import get_db, verify_bearer
from devault.api.schemas import ScheduleCreate, ScheduleOut, SchedulePatch
from devault.db.models import Schedule
from devault.services import control as control_svc

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.post("", dependencies=[Depends(verify_bearer)], response_model=ScheduleOut, summary="Create schedule")
def create_schedule(body: ScheduleCreate, db: Session = Depends(get_db)) -> Schedule:
    return control_svc.create_schedule(db, body)


@router.get("", dependencies=[Depends(verify_bearer)], response_model=list[ScheduleOut], summary="List schedules")
def list_schedules(db: Session = Depends(get_db)) -> list[Schedule]:
    return list(db.scalars(select(Schedule).order_by(Schedule.created_at.desc())).all())


@router.get(
    "/{schedule_id}",
    dependencies=[Depends(verify_bearer)],
    response_model=ScheduleOut,
    summary="Get schedule",
)
def get_schedule(schedule_id: uuid.UUID, db: Session = Depends(get_db)) -> Schedule:
    s = db.get(Schedule, schedule_id)
    if s is None:
        raise HTTPException(404, detail="schedule not found")
    return s


@router.patch(
    "/{schedule_id}",
    dependencies=[Depends(verify_bearer)],
    response_model=ScheduleOut,
    summary="Update schedule",
)
def patch_schedule(
    schedule_id: uuid.UUID,
    body: SchedulePatch,
    db: Session = Depends(get_db),
) -> Schedule:
    return control_svc.patch_schedule(db, schedule_id, body)


@router.delete("/{schedule_id}", dependencies=[Depends(verify_bearer)], summary="Delete schedule")
def delete_schedule(schedule_id: uuid.UUID, db: Session = Depends(get_db)) -> dict[str, str]:
    control_svc.delete_schedule(db, schedule_id)
    return {"status": "deleted"}
