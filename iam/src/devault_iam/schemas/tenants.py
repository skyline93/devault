from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class TenantOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    plan: str
    status: str

    model_config = {"from_attributes": True}


class TenantCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9-]+$")


class TenantPatchIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    plan: str | None = Field(default=None, max_length=64)
    status: str | None = Field(default=None, max_length=32)


class MemberOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    email: str
    role: str
    status: str

    model_config = {"from_attributes": False}


class MemberCreateIn(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    role: str = Field(pattern=r"^(tenant_admin|operator|auditor|platform_admin)$")


class MemberPatchIn(BaseModel):
    role: str = Field(pattern=r"^(tenant_admin|operator|auditor|platform_admin)$")
