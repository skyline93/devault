from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from devault.api.deps import get_auth_context, get_db
from devault.api.schemas import AuthSessionOut
from devault.security.auth_context import AuthContext
from devault.services.auth_session_payload import build_auth_session_out

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get(
    "/session",
    response_model=AuthSessionOut,
    summary="Current session principal",
    description=(
        "Returns the authenticated principal from `Authorization: Bearer` when IAM JWT validation is "
        "configured (`DEVAULT_IAM_JWT_*` + JWKS or PEM). When IAM is not configured, returns the "
        "dev-open admin principal for local development."
    ),
)
def get_auth_session(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
) -> AuthSessionOut:
    return build_auth_session_out(auth, db)
