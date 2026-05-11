from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, Field


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
    tenant_id: uuid.UUID | None = None
    permissions: list[str]
    must_change_password: bool = False


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=12)


class MfaEnrollStartOut(BaseModel):
    secret: str
    otpauth_uri: str


class MfaConfirmIn(BaseModel):
    secret: str
    code: str


class MfaDisableIn(BaseModel):
    password: str
    code: str
