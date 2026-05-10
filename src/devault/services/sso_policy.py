from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from devault.db.models import Tenant


def tenant_oidc_issuer_audience_in_use(
    db: Session,
    *,
    issuer: str | None,
    audience: str | None,
    exclude_tenant_id: uuid.UUID | None = None,
) -> bool:
    if not (issuer and audience):
        return False
    iss = issuer.strip().rstrip("/")
    aud = audience.strip()
    stmt = select(Tenant.id).where(Tenant.sso_oidc_issuer == iss, Tenant.sso_oidc_audience == aud)
    if exclude_tenant_id is not None:
        stmt = stmt.where(Tenant.id != exclude_tenant_id)
    return db.scalar(stmt) is not None
