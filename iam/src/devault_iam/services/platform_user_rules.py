"""Rules for users with ``is_platform_admin`` (zero tenant memberships)."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from devault_iam.db.models import TenantMember, User


def ensure_user_may_receive_tenant_membership(user: User) -> None:
    """Raise ValueError if this user must not hold a tenant_members row."""
    if user.is_platform_admin:
        raise ValueError("platform_user_cannot_join_tenant")


def count_active_memberships(db: Session, user_id: uuid.UUID) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(TenantMember)
            .where(TenantMember.user_id == user_id, TenantMember.status == "active")
        )
        or 0
    )


def ensure_user_has_no_active_memberships(db: Session, user_id: uuid.UUID) -> None:
    """Platform admins must have zero active tenant memberships."""
    if count_active_memberships(db, user_id) > 0:
        raise ValueError("user_has_active_tenant_memberships")
