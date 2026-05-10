from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from devault_iam.api.deps import get_db
from devault_iam.repositories.rbac import RbacRepository
from devault_iam.services.readiness import database_ready

router = APIRouter(prefix="/v1", tags=["ready"])

_MIN_PERMISSIONS = 6


@router.get("/ready")
def ready(db: Session = Depends(get_db)) -> dict[str, object]:
    """Kubernetes-style readiness: DB up + RBAC seed present."""
    if not database_ready(db):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database_unavailable",
        )
    rbac = RbacRepository(db)
    perm_count = rbac.count_permissions()
    ta = rbac.get_role_by_name_global("tenant_admin")
    if perm_count < _MIN_PERMISSIONS or ta is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="rbac_seed_missing",
        )
    rpc = rbac.role_permission_count(ta.id)
    if rpc < 1:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="rbac_seed_missing",
        )
    return {"status": "ready", "permissions": perm_count, "tenant_admin_permissions": rpc}


@router.get("/readyz")
def readyz() -> dict[str, str]:
    """Liveness: process up (no external dependencies)."""
    return {"status": "ok"}
