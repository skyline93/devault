from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: uuid.UUID
    created_at: datetime
    action: str
    outcome: str
    actor_user_id: uuid.UUID | None
    tenant_id: uuid.UUID | None
    resource_type: str | None
    resource_id: str | None
    detail: str | None
    request_id: str | None
    ip: str | None
    user_agent: str | None = None
    context_json: dict[str, Any] | None = None

    model_config = {"from_attributes": True}
