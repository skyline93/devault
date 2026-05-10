from __future__ import annotations

import uuid
from typing import Literal

from sqlalchemy.orm import Session

from devault.api.schemas import AuthSessionOut, SessionTenantRow
from devault.db.models import Tenant
from devault.security.auth_context import AuthContext


def _membership_role_iam(perm: frozenset[str]) -> Literal["tenant_admin", "operator", "auditor"]:
    if "devault.console.admin" in perm or "devault.platform.admin" in perm:
        return "tenant_admin"
    if "devault.console.write" in perm or "devault.control.write" in perm:
        return "operator"
    return "auditor"


def _iam_human_auth_session_out(auth: AuthContext, db: Session) -> AuthSessionOut:
    assert auth.user_id is not None
    role_pub = _membership_role_iam(auth.iam_perm)
    allowed_ids = sorted(auth.allowed_tenant_ids or frozenset(), key=lambda u: u.hex)
    tenants_out: list[SessionTenantRow] = []
    for tid in allowed_ids:
        t = db.get(Tenant, tid)
        if t is None:
            continue
        tenants_out.append(
            SessionTenantRow(
                tenant_id=t.id,
                slug=t.slug,
                name=t.name,
                membership_role=role_pub,
                require_mfa_for_admins=bool(t.require_mfa_for_admins),
                sso_password_login_disabled=bool(t.sso_password_login_disabled),
            )
        )
    return AuthSessionOut(
        role=auth.role,
        principal_label=auth.principal_label,
        allowed_tenant_ids=allowed_ids,
        principal_kind="tenant_user",
        user_id=auth.user_id,
        email=None,
        tenants=tenants_out if tenants_out else None,
        needs_mfa=auth.principal_kind == "tenant_user" and not auth.mfa_satisfied,
    )


def build_auth_session_out(auth: AuthContext, db: Session) -> AuthSessionOut:
    if auth.principal_kind == "platform":
        ids: list[uuid.UUID] | None = None
        if auth.allowed_tenant_ids is not None:
            ids = sorted(auth.allowed_tenant_ids, key=lambda u: u.hex)
        return AuthSessionOut(
            role=auth.role,
            principal_label=auth.principal_label,
            allowed_tenant_ids=ids,
            principal_kind="platform",
            user_id=None,
            email=None,
            tenants=None,
            needs_mfa=False,
        )

    if auth.principal_label.startswith("iam:user:"):
        return _iam_human_auth_session_out(auth, db)

    raise RuntimeError(f"unsupported tenant principal: {auth.principal_label!r}")
