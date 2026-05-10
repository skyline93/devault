from __future__ import annotations

import uuid
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from devault_iam.db.models import Permission, Role, RolePermission, Tenant, TenantMember, User


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
    pa = get_template_role(db, "platform_admin")
    if pa is None:
        return False
    m = db.scalar(
        select(TenantMember.id).where(
            TenantMember.user_id == user_id,
            TenantMember.role_id == pa.id,
            TenantMember.status == "active",
        )
    )
    return m is not None


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
    keys: set[str] = set()
    for m in active_memberships(db, user_id):
        keys.update(permission_keys_for_role(db, m.role_id))
    return sorted(keys)


def tenant_ids_for_user(db: Session, user_id: uuid.UUID) -> list[uuid.UUID]:
    return sorted({m.tenant_id for m in active_memberships(db, user_id)}, key=lambda u: u.hex)


def principal_kind_for_user(db: Session, user_id: uuid.UUID) -> Literal["platform", "tenant_user"]:
    return "platform" if user_is_platform(db, user_id) else "tenant_user"


def get_default_tenant(db: Session) -> Tenant | None:
    return db.scalar(select(Tenant).where(Tenant.slug == "default"))


def resolve_effective_tenant_id(
    db: Session,
    user_id: uuid.UUID,
    *,
    requested_tenant_id: uuid.UUID | None,
    default_tenant_slug: str = "default",
) -> uuid.UUID:
    tids = tenant_ids_for_user(db, user_id)
    if not tids:
        raise PermissionError("user has no tenant memberships")
    if requested_tenant_id is not None:
        if requested_tenant_id in tids:
            return requested_tenant_id
    t = db.scalar(select(Tenant).where(Tenant.slug == default_tenant_slug))
    if t is not None and t.id in tids:
        return t.id
    return tids[0]


def verify_tenant_header_matches_token(
    token_tid: uuid.UUID,
    header_tid: uuid.UUID | None,
) -> None:
    if header_tid is None:
        return
    if header_tid != token_tid:
        raise PermissionError("X-DeVault-Tenant-Id does not match access token tid")


def load_user_active(db: Session, user_id: uuid.UUID) -> User | None:
    u = db.get(User, user_id)
    if u is None or u.status != "active":
        return None
    return u
