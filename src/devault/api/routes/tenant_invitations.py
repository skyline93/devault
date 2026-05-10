from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from devault.api.deps import ensure_platform_or_tenant_admin_for_tenant, get_auth_context, get_db
from devault.api.schemas import TenantInvitationCreate, TenantInvitationOut
from devault.db.models import Tenant, TenantInvitation
from devault.security.auth_context import AuthContext
from devault.services.auth_audit import auth_audit
from devault.services.email_delivery import send_plain_email
from devault.services.login_rate_limit import check_sliding_rate_limit
from devault.services.tenant_invitation_flow import (
    create_invitation_row,
    revoke_pending_invitations_for_email,
)
from devault.settings import Settings, get_settings

router = APIRouter()


def _invitation_link_base(settings: Settings) -> str:
    b = (settings.invitation_link_base or "").strip()
    if b:
        return b.rstrip("/")
    return (settings.password_reset_link_base or "").strip().rstrip("/")


@router.post(
    "/{tenant_id}/invitations",
    response_model=TenantInvitationOut,
    status_code=status.HTTP_201_CREATED,
    summary="Invite a user to join a tenant by email (§十六-11)",
)
def create_tenant_invitation(
    tenant_id: uuid.UUID,
    body: TenantInvitationCreate,
    request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
) -> TenantInvitation:
    ensure_platform_or_tenant_admin_for_tenant(auth, tenant_id)
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant not found")

    settings = get_settings()
    ip = request.client.host if request.client else "unknown"
    check_sliding_rate_limit(
        settings.redis_url,
        ip,
        max_per_minute=settings.auth_login_rate_limit_per_minute,
        key_prefix="devault:invite_create_rl",
    )

    revoke_pending_invitations_for_email(db, tenant_id=tenant_id, email=body.email)
    invited_by = auth.user_id if auth.principal_kind == "tenant_user" else None
    row, raw = create_invitation_row(
        db,
        tenant_id=tenant_id,
        email=body.email,
        role=body.role,
        invited_by_user_id=invited_by,
        ttl_hours=settings.invitation_ttl_hours,
    )
    db.commit()
    db.refresh(row)

    base = _invitation_link_base(settings)
    link = (
        f"{base}/user/accept-invite?token={raw}"
        if base
        else f"(configure DEVAULT_INVITATION_LINK_BASE or DEVAULT_PASSWORD_RESET_LINK_BASE) /user/accept-invite?token={raw}"
    )
    send_plain_email(
        settings,
        to_addr=body.email,
        subject=f"Invitation to DeVault tenant {tenant.slug}",
        body=(
            f"You have been invited to join tenant {tenant.name} ({tenant.slug}) on DeVault.\n\n"
            f"Open this link to accept (sign in or set your password):\n{link}\n\n"
            "If you did not expect this message, you can ignore it."
        ),
    )
    auth_audit(
        "tenant_invitation_create",
        tenant_id=str(tenant_id),
        email=body.email,
        role=body.role,
        invited_by=str(invited_by) if invited_by else None,
    )
    return row


@router.get(
    "/{tenant_id}/invitations",
    response_model=list[TenantInvitationOut],
    summary="List pending invitations for a tenant",
)
def list_pending_invitations(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
) -> list[TenantInvitation]:
    ensure_platform_or_tenant_admin_for_tenant(auth, tenant_id)
    rows = list(
        db.scalars(
            select(TenantInvitation)
            .where(
                TenantInvitation.tenant_id == tenant_id,
                TenantInvitation.accepted_at.is_(None),
            )
            .order_by(TenantInvitation.created_at.desc())
        ).all(),
    )
    return rows
