from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Literal

from fastapi import HTTPException, status

RoleName = Literal["admin", "operator", "auditor"]
PrincipalKind = Literal["platform", "tenant_user"]


@dataclass(frozen=True, slots=True)
class AuthContext:
    """Resolved HTTP/gRPC principal after session cookie or Bearer validation."""

    role: RoleName
    allowed_tenant_ids: frozenset[uuid.UUID] | None
    principal_label: str
    principal_kind: PrincipalKind = "platform"
    user_id: uuid.UUID | None = None
    mfa_satisfied: bool = True
    iam_perm: frozenset[str] = field(default_factory=frozenset)

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    def can_write(self) -> bool:
        return self.role in ("admin", "operator")

    def ensure_tenant_access(self, tenant_id: uuid.UUID) -> None:
        if self.allowed_tenant_ids is None:
            return
        if tenant_id not in self.allowed_tenant_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="principal is not allowed for this tenant",
            )

    def ensure_can_write(self) -> None:
        if self.principal_kind == "tenant_user" and not self.mfa_satisfied:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="mfa_required",
            )
        if not self.can_write():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="read-only principal cannot perform this action",
            )

    def ensure_admin(self) -> None:
        if self.principal_kind != "platform":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="platform administrator required",
            )
        if self.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="admin role required",
            )


def dev_open_auth_context() -> AuthContext:
    """When DEVAULT_API_TOKEN is unset (local dev), allow full access without Bearer."""
    return AuthContext(role="admin", allowed_tenant_ids=None, principal_label="dev-open")


def legacy_token_context() -> AuthContext:
    """Single DEVAULT_API_TOKEN (legacy) acts as platform admin for all tenants."""
    return AuthContext(role="admin", allowed_tenant_ids=None, principal_label="legacy-api-token")
