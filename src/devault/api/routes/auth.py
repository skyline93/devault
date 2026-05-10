from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from devault.api.deps import get_auth_context
from devault.api.schemas import AuthSessionOut
from devault.security.auth_context import AuthContext

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get(
    "/session",
    response_model=AuthSessionOut,
    summary="Current session principal",
    description=(
        "Returns the authenticated principal derived from `Authorization: Bearer` "
        "(API key, legacy `DEVAULT_API_TOKEN`, or OIDC JWT when configured). "
        "When authentication is disabled (no API keys and no platform token), returns the dev-open admin principal."
    ),
)
def get_auth_session(auth: AuthContext = Depends(get_auth_context)) -> AuthSessionOut:
    allowed = auth.allowed_tenant_ids
    ids: list[uuid.UUID] | None = None
    if allowed is not None:
        ids = sorted(allowed, key=lambda u: u.hex)
    return AuthSessionOut(
        role=auth.role,
        principal_label=auth.principal_label,
        allowed_tenant_ids=ids,
    )
