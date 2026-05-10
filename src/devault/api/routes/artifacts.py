from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from devault.api.deps import (
    ensure_platform_or_tenant_admin_for_tenant,
    get_auth_context,
    get_db,
    get_effective_tenant,
)
from devault.api.schemas import ArtifactLegalHoldPatch, ArtifactOut
from devault.db.models import Artifact, Tenant
from devault.security.auth_context import AuthContext
from devault.services import control as control_svc

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


@router.patch("/{artifact_id}/legal-hold", response_model=ArtifactOut, summary="Set legal hold (admin)")
def patch_artifact_legal_hold(
    artifact_id: uuid.UUID,
    body: ArtifactLegalHoldPatch,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant),
    auth: AuthContext = Depends(get_auth_context),
) -> Artifact:
    ensure_platform_or_tenant_admin_for_tenant(auth, tenant.id)
    return control_svc.patch_artifact_legal_hold(
        db,
        artifact_id,
        tenant_id=tenant.id,
        legal_hold=body.legal_hold,
    )
