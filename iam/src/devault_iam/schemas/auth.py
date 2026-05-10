from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)
    name: str | None = Field(default=None, max_length=255)


class LoginIn(BaseModel):
    email: EmailStr
    password: str
    mfa_code: str | None = None
    tenant_id: uuid.UUID | None = None


class RefreshIn(BaseModel):
    refresh_token: str
    tenant_id: uuid.UUID | None = None


class LogoutIn(BaseModel):
    refresh_token: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    tenant_id: uuid.UUID
    permissions: list[str]


class MfaEnrollStartOut(BaseModel):
    secret: str
    otpauth_uri: str


class MfaConfirmIn(BaseModel):
    secret: str
    code: str


class MfaDisableIn(BaseModel):
    password: str
    code: str
