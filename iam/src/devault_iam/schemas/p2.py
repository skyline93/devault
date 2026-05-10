from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class SubjectIn(BaseModel):
    type: Literal["user", "api_key"]
    id: uuid.UUID


class AuthorizeIn(BaseModel):
    subject: SubjectIn
    tenant_id: uuid.UUID
    action: str = Field(min_length=1, max_length=256)
    resource: dict[str, Any] | None = None


class AuthorizeOut(BaseModel):
    allowed: bool


class ApiKeyCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    scopes: list[str] = Field(min_length=1)
    expires_in_days: int | None = Field(default=None, ge=1, le=3650)


class ApiKeySummaryOut(BaseModel):
    id: uuid.UUID
    name: str
    key_prefix: str
    tenant_id: uuid.UUID | None
    enabled: bool
    expires_at: datetime | None

    model_config = {"from_attributes": True}


class ApiKeyCreatedOut(ApiKeySummaryOut):
    secret: str


class ApiKeyPatchIn(BaseModel):
    enabled: bool


class ApiKeyGrantIn(BaseModel):
    grant_type: Literal["api_key"] = "api_key"
    api_key: str = Field(min_length=10)


class ApiKeyTokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    tenant_id: uuid.UUID | None = None
    permissions: list[str]
