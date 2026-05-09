from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from devault.api.deps import get_db, get_effective_tenant
from devault.api.schemas import ArtifactOut
from devault.db.models import Artifact, Tenant

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


@router.get("/{artifact_id}", response_model=ArtifactOut, summary="Get artifact")
def get_artifact(
    artifact_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant),
) -> Artifact:
    art = db.get(Artifact, artifact_id)
    if art is None or art.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="artifact not found")
    return art


@router.get("", response_model=list[ArtifactOut], summary="List artifacts")
def list_artifacts(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[Artifact]:
    stmt = (
        select(Artifact)
        .where(Artifact.tenant_id == tenant.id)
        .order_by(Artifact.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(stmt).all())
