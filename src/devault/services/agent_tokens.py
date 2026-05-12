"""Tenant-scoped Agent bearer tokens (hashed at rest)."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from devault.db.models import AgentToken


def hash_agent_token(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


def mint_agent_token_secret() -> str:
    return secrets.token_urlsafe(48)


def get_agent_token_by_hash(db: Session, token_hash: str) -> AgentToken | None:
    return db.scalar(select(AgentToken).where(AgentToken.token_hash == token_hash))


def agent_token_is_usable(row: AgentToken, *, now: datetime | None = None) -> bool:
    ts = now or datetime.now(timezone.utc)
    if row.disabled_at is not None:
        return False
    if row.expires_at is not None and row.expires_at <= ts:
        return False
    return True


def create_agent_token(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    label: str,
    description: str | None = None,
    expires_at: datetime | None = None,
) -> tuple[AgentToken, str]:
    plaintext = mint_agent_token_secret()
    now = datetime.now(timezone.utc)
    row = AgentToken(
        tenant_id=tenant_id,
        token_hash=hash_agent_token(plaintext),
        label=label.strip(),
        description=(description or "").strip() or None,
        expires_at=expires_at,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    return row, plaintext


def touch_agent_token_used(db: Session, row: AgentToken, *, now: datetime | None = None) -> None:
    row.last_used_at = now or datetime.now(timezone.utc)
    row.updated_at = row.last_used_at


def set_agent_token_disabled(db: Session, row: AgentToken, *, disabled: bool) -> None:
    now = datetime.now(timezone.utc)
    row.disabled_at = now if disabled else None
    row.updated_at = now


def count_instances_for_token(db: Session, token_id: uuid.UUID) -> int:
    from devault.db.models import EdgeAgent

    return int(
        db.scalar(
            select(func.count()).select_from(EdgeAgent).where(EdgeAgent.agent_token_id == token_id),
        )
        or 0,
    )
