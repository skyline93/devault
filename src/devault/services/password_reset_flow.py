from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from devault.db.models import ConsoleUser, PasswordResetToken
from devault.security.token_resolve import hash_api_token


def create_reset_token(db: Session, user_id: uuid.UUID, *, ttl_minutes: int) -> str:
    raw = secrets.token_urlsafe(32)
    h = hash_api_token(raw)
    now = datetime.now(timezone.utc)
    row = PasswordResetToken(
        user_id=user_id,
        token_hash=h,
        expires_at=now + timedelta(minutes=max(5, ttl_minutes)),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return raw


def find_valid_reset_token(db: Session, raw_token: str) -> PasswordResetToken | None:
    h = hash_api_token(raw_token)
    row = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == h))
    if row is None or row.used_at is not None:
        return None
    if row.expires_at < datetime.now(timezone.utc):
        return None
    return row


def load_user_for_reset(db: Session, row: PasswordResetToken) -> ConsoleUser | None:
    u = db.get(ConsoleUser, row.user_id)
    if u is None or u.disabled:
        return None
    return u
