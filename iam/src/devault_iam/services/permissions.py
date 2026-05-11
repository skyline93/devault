from __future__ import annotations

import uuid
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from devault_iam.db.models import Permission, Role, RolePermission, TenantMember, User


def get_template_role(db: Session, name: str) -> Role | None:
    return db.scalar(select(Role).where(Role.name == name, Role.tenant_id.is_(None), Role.is_system.is_(True)))


def permission_keys_for_role(db: Session, role_id: uuid.UUID) -> list[str]:
    rows = db.execute(
        select(Permission.key)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role_id)
        .order_by(Permission.key),
    ).all()
    return [r[0] for r in rows]


def active_memberships(db: Session, user_id: uuid.UUID) -> list[TenantMember]:
    return list(
        db.scalars(
            select(TenantMember).where(
                TenantMember.user_id == user_id,
                TenantMember.status == "active",
            )
        ).all()
    )


def user_is_platform(db: Session, user_id: uuid.UUID) -> bool:
    v = db.scalar(select(User.is_platform_admin).where(User.id == user_id))
    return bool(v)


def permissions_for_user_in_tenant(db: Session, user_id: uuid.UUID, tenant_id: uuid.UUID) -> list[str]:
    """RBAC permissions for one user within a single tenant (membership role only)."""
    m = db.scalar(
        select(TenantMember).where(
            TenantMember.user_id == user_id,
            TenantMember.tenant_id == tenant_id,
            TenantMember.status == "active",
        )
    )
    if m is None:
        return []
    return permission_keys_for_role(db, m.role_id)


def union_permission_keys_for_user(db: Session, user_id: uuid.UUID) -> list[str]:
    u = db.get(User, user_id)
    if u is None:
        return []
    if u.is_platform_admin:
        role = get_template_role(db, "platform_admin")
        if role is None:
            return []
        return permission_keys_for_role(db, role.id)
    keys: set[str] = set()
    for m in active_memberships(db, user_id):
        keys.update(permission_keys_for_role(db, m.role_id))
    return sorted(keys)


def tenant_ids_for_user(db: Session, user_id: uuid.UUID) -> list[uuid.UUID]:
    u = db.get(User, user_id)
    if u is not None and u.is_platform_admin:
        return []
    return sorted({m.tenant_id for m in active_memberships(db, user_id)}, key=lambda x: x.hex)


def principal_kind_for_user(db: Session, user_id: uuid.UUID) -> Literal["platform", "tenant_user"]:
    return "platform" if user_is_platform(db, user_id) else "tenant_user"


def resolve_effective_tenant_id(
    db: Session,
    user_id: uuid.UUID,
    *,
    requested_tenant_id: uuid.UUID | None,
) -> uuid.UUID:
    """Pick tenant context for a **non–platform-admin** user (must have memberships)."""
    tids = tenant_ids_for_user(db, user_id)
    if not tids:
        raise PermissionError("user has no tenant memberships")
    if requested_tenant_id is not None:
        if requested_tenant_id not in tids:
            raise PermissionError("tenant not allowed for user")
        return requested_tenant_id
    return tids[0]


def resolve_effective_tenant_for_login(
    db: Session,
    user: User,
    requested_tenant_id: uuid.UUID | None,
) -> uuid.UUID | None:
    """Login / refresh: platform admins never get a tenant ``tid``; others resolve memberships."""
    if user.is_platform_admin:
        if requested_tenant_id is not None:
            raise ValueError("platform_user_tenant_disallowed")
        return None
    try:
        return resolve_effective_tenant_id(db, user.id, requested_tenant_id=requested_tenant_id)
    except PermissionError as e:
        raise ValueError(str(e)) from e


def verify_tenant_header_matches_token(
    token_tid: uuid.UUID | None,
    header_tid: uuid.UUID | None,
) -> None:
    if header_tid is None:
        return
    if token_tid is None:
        raise PermissionError("access token has no tenant context; do not send X-DeVault-Tenant-Id")
    if header_tid != token_tid:
        raise PermissionError("X-DeVault-Tenant-Id does not match access token tid")


def load_user_active(db: Session, user_id: uuid.UUID) -> User | None:
    u = db.get(User, user_id)
    if u is None or u.status != "active":
        return None
    return u
