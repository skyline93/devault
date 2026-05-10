from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from devault_iam.api.deps import get_db
from devault_iam.api.principal import Principal, ensure_tenant_scope, get_current_principal, require_permission
from devault_iam.db.models import ApiKey
from devault_iam.schemas.p2 import ApiKeyCreatedOut, ApiKeyCreateIn, ApiKeyPatchIn, ApiKeySummaryOut
from devault_iam.services import api_key_service
from devault_iam.services.audit_service import record_audit_event
from devault_iam.services.permission_cache import invalidate_api_key
from devault_iam.settings import Settings, get_settings

router = APIRouter(tags=["api-keys"])


def _audit_req(request: Request) -> dict:
    return {
        "request_id": getattr(request.state, "request_id", None),
        "ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    }


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _assert_can_manage_key(principal: Principal, key: ApiKey) -> None:
    if key.tenant_id is None:
        if "devault.platform.admin" not in principal.permissions:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
        return
    if key.tenant_id not in principal.tenant_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    if "devault.console.admin" not in principal.permissions:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")


def _expires_at(body: ApiKeyCreateIn) -> datetime | None:
    if body.expires_in_days is None:
        return None
    return _utcnow() + timedelta(days=int(body.expires_in_days))


@router.get("/v1/platform/api-keys", response_model=list[ApiKeySummaryOut])
def list_platform_api_keys(
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> list[ApiKey]:
    require_permission(principal, "devault.platform.admin")
    return list(db.scalars(select(ApiKey).where(ApiKey.tenant_id.is_(None)).order_by(ApiKey.created_at.desc())).all())


@router.post("/v1/platform/api-keys", response_model=ApiKeyCreatedOut, status_code=status.HTTP_201_CREATED)
def create_platform_api_key(
    request: Request,
    body: ApiKeyCreateIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> ApiKeyCreatedOut:
    require_permission(principal, "devault.platform.admin")
    try:
        row, secret = api_key_service.create_api_key(
            db,
            tenant_id=None,
            name=body.name,
            scope_keys=body.scopes,
            created_by_user_id=principal.user_id,
            expires_at=_expires_at(body),
        )
    except ValueError as e:
        msg = str(e)
        if msg.startswith("unknown_permission"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg) from e
        if msg == "scopes_required":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg) from e
        raise
    record_audit_event(
        action="api_key.create",
        outcome="success",
        actor_user_id=principal.user_id,
        resource_type="api_key",
        resource_id=str(row.id),
        context={"name": row.name, "scope_count": len(body.scopes), "scope": "platform"},
        **_audit_req(request),
    )
    return ApiKeyCreatedOut(
        id=row.id,
        name=row.name,
        key_prefix=row.key_prefix,
        tenant_id=row.tenant_id,
        enabled=row.enabled,
        expires_at=row.expires_at,
        secret=secret,
    )


@router.get("/v1/tenants/{tenant_id}/api-keys", response_model=list[ApiKeySummaryOut])
def list_tenant_api_keys(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> list[ApiKey]:
    ensure_tenant_scope(principal, tenant_id)
    require_permission(principal, "devault.console.admin")
    return list(
        db.scalars(select(ApiKey).where(ApiKey.tenant_id == tenant_id).order_by(ApiKey.created_at.desc())).all()
    )


@router.post(
    "/v1/tenants/{tenant_id}/api-keys",
    response_model=ApiKeyCreatedOut,
    status_code=status.HTTP_201_CREATED,
)
def create_tenant_api_key(
    request: Request,
    tenant_id: uuid.UUID,
    body: ApiKeyCreateIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> ApiKeyCreatedOut:
    ensure_tenant_scope(principal, tenant_id)
    require_permission(principal, "devault.console.admin")
    try:
        row, secret = api_key_service.create_api_key(
            db,
            tenant_id=tenant_id,
            name=body.name,
            scope_keys=body.scopes,
            created_by_user_id=principal.user_id,
            expires_at=_expires_at(body),
        )
    except ValueError as e:
        msg = str(e)
        if msg.startswith("unknown_permission"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg) from e
        if msg == "scopes_required":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg) from e
        raise
    record_audit_event(
        action="api_key.create",
        outcome="success",
        actor_user_id=principal.user_id,
        tenant_id=tenant_id,
        resource_type="api_key",
        resource_id=str(row.id),
        context={"name": row.name, "scope_count": len(body.scopes), "scope": "tenant"},
        **_audit_req(request),
    )
    return ApiKeyCreatedOut(
        id=row.id,
        name=row.name,
        key_prefix=row.key_prefix,
        tenant_id=row.tenant_id,
        enabled=row.enabled,
        expires_at=row.expires_at,
        secret=secret,
    )


@router.patch("/v1/api-keys/{key_id}", response_model=ApiKeySummaryOut)
def patch_api_key(
    request: Request,
    key_id: uuid.UUID,
    body: ApiKeyPatchIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
    settings: Settings = Depends(get_settings),
) -> ApiKey:
    row = db.get(ApiKey, key_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="api_key_not_found")
    _assert_can_manage_key(principal, row)
    out = api_key_service.set_api_key_enabled(db, key_id, body.enabled)
    assert out is not None
    invalidate_api_key(settings.redis_url, key_id)
    record_audit_event(
        action="api_key.update",
        outcome="success",
        actor_user_id=principal.user_id,
        tenant_id=row.tenant_id,
        resource_type="api_key",
        resource_id=str(key_id),
        context={"enabled": body.enabled},
        **_audit_req(request),
    )
    return out


@router.delete("/v1/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_api_key_route(
    request: Request,
    key_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
    settings: Settings = Depends(get_settings),
) -> None:
    row = db.get(ApiKey, key_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="api_key_not_found")
    _assert_can_manage_key(principal, row)
    tid = row.tenant_id
    api_key_service.delete_api_key(db, key_id)
    invalidate_api_key(settings.redis_url, key_id)
    record_audit_event(
        action="api_key.delete",
        outcome="success",
        actor_user_id=principal.user_id,
        tenant_id=tid,
        resource_type="api_key",
        resource_id=str(key_id),
        **_audit_req(request),
    )
