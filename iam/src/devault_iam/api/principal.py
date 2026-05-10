from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Annotated, Literal

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from devault_iam.api.deps import get_db
from devault_iam.security.jwt_tokens import decode_access_token
from devault_iam.services import permissions as perm_svc
from devault_iam.services.permissions import load_user_active

_http_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class Principal:
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    tenant_ids: frozenset[uuid.UUID]
    permissions: frozenset[str]
    principal_kind: Literal["platform", "tenant_user"]
    mfa_satisfied: bool
    email: str


def get_jwt_pem(request: Request) -> tuple[str, str]:
    priv = getattr(request.app.state, "jwt_private_pem", None)
    pub = getattr(request.app.state, "jwt_public_pem", None)
    if not isinstance(priv, str) or not isinstance(pub, str) or not priv.strip() or not pub.strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="jwt_not_configured",
        )
    return priv, pub


def get_current_principal(
    request: Request,
    db: Session = Depends(get_db),
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_http_bearer)] = None,
) -> Principal:
    from devault_iam.settings import get_settings

    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_bearer")
    token = creds.credentials.strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_bearer")
    _, pub = get_jwt_pem(request)
    settings = get_settings()
    try:
        payload = decode_access_token(token=token, public_key_pem=pub, settings=settings)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token") from None

    try:
        sub_raw = str(payload["sub"])
        if sub_raw.startswith("api_key:"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="user_bearer_required",
            )
        uid = uuid.UUID(sub_raw)
        tid_raw = payload.get("tid")
        if tid_raw is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token")
        tid = uuid.UUID(str(tid_raw))
    except HTTPException:
        raise
    except (KeyError, ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token") from None

    user = load_user_active(db, uid)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user_inactive")

    allowed_tids = perm_svc.tenant_ids_for_user(db, uid)
    if tid not in allowed_tids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="tenant_not_allowed")

    tids = frozenset(allowed_tids)
    perms = frozenset(perm_svc.union_permission_keys_for_user(db, uid))
    pk = perm_svc.principal_kind_for_user(db, uid)
    mfa_sat = (not user.mfa_enabled) or (user.totp_confirmed_at is not None)

    return Principal(
        user_id=uid,
        tenant_id=tid,
        tenant_ids=tids,
        permissions=perms,
        principal_kind=pk,
        mfa_satisfied=mfa_sat,
        email=user.email,
    )


def parse_optional_tenant_header(
    x_devault: str | None,
    x_tenant: str | None,
) -> uuid.UUID | None:
    raw = (x_devault or x_tenant or "").strip()
    if not raw:
        return None
    try:
        return uuid.UUID(raw)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid_tenant_header",
        ) from None


def require_permission(principal: Principal, key: str) -> None:
    if key not in principal.permissions:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")


def ensure_tenant_scope(principal: Principal, tenant_id: uuid.UUID) -> None:
    if tenant_id not in principal.tenant_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="tenant_not_allowed")
