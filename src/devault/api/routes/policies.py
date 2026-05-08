from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from devault.api.deps import get_db, verify_bearer
from devault.api.schemas import PolicyCreate, PolicyOut, PolicyPatch
from devault.db.models import Policy
from devault.services import control as control_svc

router = APIRouter(prefix="/policies", tags=["policies"])


@router.post("", dependencies=[Depends(verify_bearer)], response_model=PolicyOut, summary="Create policy")
def create_policy(body: PolicyCreate, db: Session = Depends(get_db)) -> Policy:
    return control_svc.create_policy(db, body)


@router.get("", dependencies=[Depends(verify_bearer)], response_model=list[PolicyOut], summary="List policies")
def list_policies(db: Session = Depends(get_db)) -> list[Policy]:
    return list(db.scalars(select(Policy).order_by(Policy.created_at.desc())).all())


@router.get(
    "/{policy_id}",
    dependencies=[Depends(verify_bearer)],
    response_model=PolicyOut,
    summary="Get policy",
)
def get_policy(policy_id: uuid.UUID, db: Session = Depends(get_db)) -> Policy:
    p = db.get(Policy, policy_id)
    if p is None:
        raise HTTPException(404, detail="policy not found")
    return p


@router.patch(
    "/{policy_id}",
    dependencies=[Depends(verify_bearer)],
    response_model=PolicyOut,
    summary="Update policy",
)
def patch_policy(
    policy_id: uuid.UUID,
    body: PolicyPatch,
    db: Session = Depends(get_db),
) -> Policy:
    return control_svc.patch_policy(db, policy_id, body)


@router.delete("/{policy_id}", dependencies=[Depends(verify_bearer)], summary="Delete policy")
def delete_policy(policy_id: uuid.UUID, db: Session = Depends(get_db)) -> dict[str, str]:
    control_svc.delete_policy(db, policy_id)
    return {"status": "deleted"}
