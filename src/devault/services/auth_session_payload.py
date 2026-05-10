from __future__ import annotations

import uuid
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from devault.api.schemas import AuthSessionOut, SessionTenantRow
from devault.db.models import ConsoleUser, Tenant, TenantMembership
from devault.security.auth_context import AuthContext


def _membership_role_public(raw: str) -> Literal["tenant_admin", "operator", "auditor"]:
    s = raw.strip().lower()
    if s == "tenant_admin":
        return "tenant_admin"
    if s == "auditor":
        return "auditor"
    return "operator"


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

    assert auth.user_id is not None
    user = db.get(ConsoleUser, auth.user_id)
    if user is None:
        raise RuntimeError("console user referenced by auth context is missing")

    stmt = (
        select(TenantMembership, Tenant)
        .join(Tenant, Tenant.id == TenantMembership.tenant_id)
        .where(TenantMembership.user_id == user.id)
        .order_by(Tenant.slug.asc())
    )
    rows = list(db.execute(stmt).all())
    tenants_out: list[SessionTenantRow] = []
    allowed_ids: list[uuid.UUID] = []
    for m, t in rows:
        allowed_ids.append(t.id)
        tenants_out.append(
            SessionTenantRow(
                tenant_id=t.id,
                slug=t.slug,
                name=t.name,
                membership_role=_membership_role_public(m.role),
                require_mfa_for_admins=bool(t.require_mfa_for_admins),
                sso_password_login_disabled=bool(t.sso_password_login_disabled),
            )
        )

    return AuthSessionOut(
        role=auth.role,
        principal_label=auth.principal_label,
        allowed_tenant_ids=sorted(allowed_ids, key=lambda u: u.hex),
        principal_kind="tenant_user",
        user_id=user.id,
        email=user.email,
        tenants=tenants_out,
        needs_mfa=auth.principal_kind == "tenant_user" and not auth.mfa_satisfied,
    )
