from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from devault.api.deps import get_db, verify_bearer
from devault.api.schemas import ArtifactOut
from devault.db.models import Artifact

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


@router.get("/{artifact_id}", dependencies=[Depends(verify_bearer)], response_model=ArtifactOut)
def get_artifact(artifact_id: uuid.UUID, db: Session = Depends(get_db)) -> Artifact:
    art = db.get(Artifact, artifact_id)
    if art is None:
        raise HTTPException(status_code=404, detail="artifact not found")
    return art


@router.get("", dependencies=[Depends(verify_bearer)], response_model=list[ArtifactOut])
def list_artifacts(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[Artifact]:
    stmt = (
        select(Artifact).order_by(Artifact.created_at.desc()).limit(limit).offset(offset)
    )
    return list(db.scalars(stmt).all())
