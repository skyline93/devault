from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from devault_iam.api.deps import get_db
from devault_iam.schemas.p2 import AuthorizeIn, AuthorizeOut
from devault_iam.security.rate_limit import check_sliding_rate_limit
from devault_iam.services.authorize_logic import is_action_allowed
from devault_iam.settings import Settings, get_settings

router = APIRouter(prefix="/v1", tags=["authorize"])


def _check_internal_api(request: Request, settings: Settings) -> None:
    token = (settings.internal_api_token or "").strip()
    if not token:
        return
    if request.headers.get("X-Iam-Internal") != token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="internal_token_required",
        )


def _client_ip(request: Request) -> str | None:
    if request.client:
        return request.client.host
    return None


@router.post("/authorize", response_model=AuthorizeOut)
def post_authorize(
    request: Request,
    body: AuthorizeIn,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthorizeOut:
    _check_internal_api(request, settings)
    ip = _client_ip(request) or "unknown"
    try:
        check_sliding_rate_limit(
            settings.redis_url,
            ip,
            max_per_minute=settings.authorize_rate_limit_per_minute,
            key_prefix="devault_iam:authorize_rl",
        )
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="rate_limited") from None

    allowed = is_action_allowed(
        db,
        settings,
        subject_type=body.subject.type,
        subject_id=body.subject.id,
        tenant_id=body.tenant_id,
        action=body.action,
        _resource=body.resource,
    )
    return AuthorizeOut(allowed=allowed)
