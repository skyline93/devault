from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from devault.db.models import ControlPlaneApiKey
from devault.settings import Settings


def authentication_enabled(settings: Settings, db: Session) -> bool:
    if settings.api_token:
        return True
    if (settings.oidc_issuer or "").strip() and (settings.oidc_audience or "").strip():
        return True
    return db.scalar(select(ControlPlaneApiKey.id).limit(1)) is not None
