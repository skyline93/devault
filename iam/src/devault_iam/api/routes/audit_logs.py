from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from devault_iam.api.deps import get_db
from devault_iam.api.principal import Principal, get_current_principal, require_permission
from devault_iam.schemas.audit import AuditLogOut
from devault_iam.services import audit_service

router = APIRouter(tags=["audit"])


@router.get("/v1/platform/audit-logs", response_model=list[AuditLogOut])
def list_platform_audit_logs(
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    action_prefix: str | None = Query(default=None, max_length=128),
) -> list[AuditLogOut]:
    require_permission(principal, "devault.platform.admin")
    rows = audit_service.list_audit_logs(db, limit=limit, offset=offset, action_prefix=action_prefix)
    return [AuditLogOut.model_validate(r) for r in rows]
