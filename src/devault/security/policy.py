from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from devault.db.models import ConsoleUser, ControlPlaneApiKey
from devault.settings import Settings


def authentication_enabled(settings: Settings, db: Session) -> bool:
    if settings.api_token:
        return True
    if (settings.oidc_issuer or "").strip() and (settings.oidc_audience or "").strip():
        return True
    if db.scalar(select(ControlPlaneApiKey.id).limit(1)) is not None:
        return True
    # §十六: any human console user forces authenticated mode (session or Bearer).
    return db.scalar(select(ConsoleUser.id).limit(1)) is not None
