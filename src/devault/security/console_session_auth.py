from __future__ import annotations

import uuid
from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from devault.db.models import ConsoleUser, Tenant, TenantMembership
from devault.security.auth_context import AuthContext, RoleName
from devault.settings import Settings

MembershipRole = Literal["tenant_admin", "operator", "auditor"]


def _map_membership_role(raw: str) -> RoleName:
    s = raw.strip().lower()
    if s == "tenant_admin":
        return "admin"
    if s in ("operator", "auditor"):
        return s  # type: ignore[return-value]
    return "operator"


def _membership_for_tenant(
    db: Session,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> TenantMembership | None:
    return db.get(TenantMembership, (user_id, tenant_id))


def console_user_auth_context(
    db: Session,
    settings: Settings,
    *,
    user: ConsoleUser,
    effective_tenant_id: uuid.UUID,
) -> AuthContext:
    if user.disabled:
        # Caller should reject login; defensive for stale sessions.
        raise PermissionError("user disabled")
    m = _membership_for_tenant(db, user.id, effective_tenant_id)
    if m is None:
        raise PermissionError("no membership for tenant")
    role = _map_membership_role(m.role)
    rows = db.scalars(select(TenantMembership).where(TenantMembership.user_id == user.id)).all()
    allowed = frozenset(r.tenant_id for r in rows)
    label = f"user:{user.email}"
    return AuthContext(
        role=role,
        allowed_tenant_ids=allowed,
        principal_label=label,
        principal_kind="tenant_user",
        user_id=user.id,
    )


def load_user_for_session(db: Session, user_id: uuid.UUID) -> ConsoleUser | None:
    return db.get(ConsoleUser, user_id)


def resolve_effective_tenant_id_for_console_user(
    db: Session,
    settings: Settings,
    *,
    x_devault_tenant_id: str | None,
    user_id: uuid.UUID,
) -> uuid.UUID:
    """Pick tenant id used to compute session RBAC role (header, else default slug if member, else first membership)."""
    memberships = list(
        db.scalars(select(TenantMembership.tenant_id).where(TenantMembership.user_id == user_id)).all()
    )
    if not memberships:
        raise PermissionError("user has no tenant memberships")

    if x_devault_tenant_id is not None:
        raw = x_devault_tenant_id.strip()
        if raw:
            try:
                tid = uuid.UUID(raw)
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="invalid X-DeVault-Tenant-Id",
                ) from e
            if tid in memberships:
                return tid

    t = db.scalar(select(Tenant).where(Tenant.slug == settings.default_tenant_slug))
    if t is not None and t.id in memberships:
        return t.id
    return sorted(memberships, key=lambda u: u.hex)[0]
