from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class PlatformUserCreateIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12)
    name: str | None = Field(default=None, max_length=255)
    must_change_password: bool = False


class PlatformUserPatchIn(BaseModel):
    password: str | None = Field(default=None, min_length=12)
    must_change_password: bool | None = None


class PlatformUserOut(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    status: str
    is_platform_admin: bool
    must_change_password: bool
    created_at: datetime

    model_config = {"from_attributes": True}
