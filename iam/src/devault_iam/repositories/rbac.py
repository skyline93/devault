from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from devault_iam.db.models import Permission, Role, RolePermission


class RbacRepository:
    """Read-side helpers for RBAC seed verification and future Authorize."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def count_permissions(self) -> int:
        n = self._db.scalar(select(func.count()).select_from(Permission))
        return int(n or 0)

    def get_role_by_name_global(self, name: str) -> Role | None:
        return self._db.scalar(
            select(Role).where(Role.name == name, Role.tenant_id.is_(None), Role.is_system.is_(True))
        )

    def role_permission_count(self, role_id: uuid.UUID) -> int:
        n = self._db.scalar(
            select(func.count()).select_from(RolePermission).where(RolePermission.role_id == role_id)
        )
        return int(n or 0)
