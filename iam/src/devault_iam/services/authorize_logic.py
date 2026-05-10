from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from devault_iam.db.models import ApiKey, ApiKeyScope
from devault_iam.services import permissions as perm_svc
from devault_iam.services.permission_cache import (
    cache_key_api_key,
    cache_key_user,
    get_cached_string_list,
    set_cached_string_list,
)
from devault_iam.settings import Settings


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _permission_keys_for_api_key(db: Session, api_key_id: uuid.UUID) -> list[str]:
    rows = db.scalars(
        select(ApiKeyScope.permission_key)
        .where(ApiKeyScope.api_key_id == api_key_id)
        .order_by(ApiKeyScope.permission_key)
    ).all()
    return [str(x) for x in rows]


def cached_user_permissions(
    db: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> list[str]:
    key = cache_key_user(tenant_id, user_id)
    cached = get_cached_string_list(settings.redis_url, key)
    if cached is not None:
        return cached
    perms = perm_svc.permissions_for_user_in_tenant(db, user_id, tenant_id)
    set_cached_string_list(settings.redis_url, key, perms, settings.permission_cache_ttl_seconds)
    return perms


def cached_api_key_permissions(
    db: Session,
    settings: Settings,
    *,
    api_key_id: uuid.UUID,
) -> list[str]:
    key = cache_key_api_key(api_key_id)
    cached = get_cached_string_list(settings.redis_url, key)
    if cached is not None:
        return cached
    perms = _permission_keys_for_api_key(db, api_key_id)
    set_cached_string_list(settings.redis_url, key, perms, settings.permission_cache_ttl_seconds)
    return perms


def is_action_allowed(
    db: Session,
    settings: Settings,
    *,
    subject_type: Literal["user", "api_key"],
    subject_id: uuid.UUID,
    tenant_id: uuid.UUID,
    action: str,
    _resource: dict[str, Any] | None,
) -> bool:
    action = action.strip()
    if not action:
        return False
    if subject_type == "user":
        perms = cached_user_permissions(db, settings, tenant_id=tenant_id, user_id=subject_id)
        return action in perms
    if subject_type == "api_key":
        row = db.get(ApiKey, subject_id)
        if row is None or not row.enabled:
            return False
        if row.expires_at is not None:
            exp = row.expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp < _utcnow():
                return False
        if row.tenant_id is not None and row.tenant_id != tenant_id:
            return False
        perms = cached_api_key_permissions(db, settings, api_key_id=subject_id)
        return action in perms
    return False
