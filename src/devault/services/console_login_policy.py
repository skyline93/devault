from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from devault.db.models import ConsoleUser, Tenant, TenantMembership


def compute_new_session_mfa_verified(db: Session, user: ConsoleUser) -> bool:
    """
    If user has confirmed TOTP, new sessions start with mfa_verified=False until /auth/mfa/verify.
    If tenant_admin in a tenant with require_mfa_for_admins but user has no TOTP, login is blocked.
    """
    if user.totp_secret and user.totp_confirmed_at:
        return False
    stmt = (
        select(TenantMembership, Tenant)
        .join(Tenant, Tenant.id == TenantMembership.tenant_id)
        .where(TenantMembership.user_id == user.id)
    )
    for m, t in db.execute(stmt).all():
        if m.role.strip().lower() == "tenant_admin" and t.require_mfa_for_admins:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="mfa_enrollment_required",
            )
    return True
