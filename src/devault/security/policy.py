from __future__ import annotations

from sqlalchemy.orm import Session

from devault.security.iam_jwt import iam_jwt_configured
from devault.settings import Settings


def authentication_enabled(settings: Settings, db: Session) -> bool:
    """True when IAM access JWT validation is configured (issuer, audience, JWKS or PEM)."""
    _ = db
    return iam_jwt_configured(settings)
