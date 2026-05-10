from __future__ import annotations

import logging
import uuid
from typing import Any, Literal

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from devault_iam.db.models import AuditLog
from devault_iam.db.session import SessionLocal

logger = logging.getLogger("devault_iam.audit")

Outcome = Literal["success", "failure"]


def mask_email(email: str) -> str:
    """Light masking for failure logs (not cryptographic)."""
    e = email.strip().lower()
    if "@" not in e:
        return "***"
    local, _, domain = e.partition("@")
    if len(local) <= 1:
        return f"*@{domain}"
    return f"{local[0]}***@{domain}"


def record_audit_event(
    *,
    action: str,
    outcome: Outcome,
    actor_user_id: uuid.UUID | None = None,
    tenant_id: uuid.UUID | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    detail: str | None = None,
    request_id: str | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
    context: dict[str, Any] | None = None,
) -> None:
    """Persist one audit row in a **separate** DB session so caller transactions cannot roll it back."""
    row = AuditLog(
        action=action[:128],
        outcome=outcome,
        actor_user_id=actor_user_id,
        tenant_id=tenant_id,
        resource_type=(resource_type[:64] if resource_type else None),
        resource_id=(resource_id[:64] if resource_id else None),
        detail=(detail[:512] if detail else None),
        request_id=(request_id[:80] if request_id else None),
        ip=(ip[:64] if ip else None),
        user_agent=user_agent,
        context_json=context,
    )
    try:
        db = SessionLocal()
        try:
            db.add(row)
            db.commit()
        finally:
            db.close()
    except Exception:
        logger.exception("audit_write_failed action=%s", action)


def list_audit_logs(
    db: Session,
    *,
    limit: int,
    offset: int,
    action_prefix: str | None = None,
) -> list[AuditLog]:
    q = select(AuditLog).order_by(desc(AuditLog.created_at))
    if action_prefix:
        p = action_prefix.strip()
        if p:
            q = q.where(AuditLog.action.startswith(p[:128]))
    return list(db.scalars(q.limit(limit).offset(offset)).all())
