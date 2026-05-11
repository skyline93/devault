"""Test-only helpers to seed users + memberships (no HTTP register)."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from devault_iam.db.models import TenantMember, User
from devault_iam.security.passwords import hash_password
from devault_iam.services import permissions as perm_svc


def create_user_with_tenant_membership(
    db: Session,
    *,
    email: str,
    password_plain: str,
    tenant_id: uuid.UUID,
    role_name: str,
    display_name: str = "",
) -> User:
    """Insert a non–platform-admin user and an active ``TenantMember`` row."""
    email_n = email.strip().lower()
    role = perm_svc.get_template_role(db, role_name)
    if role is None:
        raise RuntimeError(f"rbac_seed_missing: role {role_name!r}")
    u = User(
        email=email_n,
        password_hash=hash_password(password_plain),
        name=(display_name or "").strip() or email_n.split("@", 1)[0],
        status="active",
        is_platform_admin=False,
    )
    db.add(u)
    db.flush()
    db.add(
        TenantMember(
            tenant_id=tenant_id,
            user_id=u.id,
            role_id=role.id,
            status="active",
        )
    )
    db.commit()
    db.refresh(u)
    return u
