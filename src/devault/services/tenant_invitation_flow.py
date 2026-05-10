from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from devault.db.models import TenantInvitation
from devault.security.token_resolve import hash_api_token


def revoke_pending_invitations_for_email(db: Session, *, tenant_id: uuid.UUID, email: str) -> None:
    db.execute(
        delete(TenantInvitation).where(
            TenantInvitation.tenant_id == tenant_id,
            TenantInvitation.email == email,
            TenantInvitation.accepted_at.is_(None),
        )
    )


def create_invitation_row(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    email: str,
    role: str,
    invited_by_user_id: uuid.UUID | None,
    ttl_hours: int,
) -> tuple[TenantInvitation, str]:
    raw = secrets.token_urlsafe(32)
    h = hash_api_token(raw)
    now = datetime.now(timezone.utc)
    row = TenantInvitation(
        tenant_id=tenant_id,
        email=email,
        role=role,
        token_hash=h,
        invited_by_user_id=invited_by_user_id,
        expires_at=now + timedelta(hours=max(1, ttl_hours)),
    )
    db.add(row)
    db.flush()
    return row, raw


def find_valid_invitation(db: Session, raw_token: str) -> TenantInvitation | None:
    h = hash_api_token(raw_token)
    row = db.scalar(select(TenantInvitation).where(TenantInvitation.token_hash == h))
    if row is None or row.accepted_at is not None:
        return None
    if row.expires_at < datetime.now(timezone.utc):
        return None
    return row
