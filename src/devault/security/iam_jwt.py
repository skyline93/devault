from __future__ import annotations

import logging
import uuid
from typing import Any

import jwt
from jwt import PyJWKClient

from devault.security.auth_context import AuthContext, RoleName
from devault.settings import Settings

logger = logging.getLogger(__name__)

_jwks_client: PyJWKClient | None = None
_jwks_client_url: str | None = None


def iam_jwt_configured(settings: Settings) -> bool:
    """Whether DeVault should require a valid IAM-issued RS256 access JWT for HTTP/gRPC (except dev-open / Agent session)."""
    if not (settings.iam_jwt_issuer or "").strip() or not (settings.iam_jwt_audience or "").strip():
        return False
    if (settings.iam_jwt_public_key_pem or "").strip():
        return True
    return bool((settings.iam_jwks_url or "").strip())


def _jwks_client(url: str) -> PyJWKClient:
    global _jwks_client, _jwks_client_url
    if _jwks_client is None or _jwks_client_url != url:
        _jwks_client = PyJWKClient(url)
        _jwks_client_url = url
    return _jwks_client


def decode_iam_access_token(raw_token: str, settings: Settings) -> dict[str, Any]:
    opts: dict[str, Any] = {"require": ["exp", "iat", "sub", "aud", "iss"]}
    issuer = (settings.iam_jwt_issuer or "").strip()
    audience = (settings.iam_jwt_audience or "").strip()
    pem = (settings.iam_jwt_public_key_pem or "").strip()
    if pem:
        return jwt.decode(
            raw_token,
            pem,
            algorithms=["RS256"],
            audience=audience,
            issuer=issuer,
            options=opts,
        )
    jwks_url = (settings.iam_jwks_url or "").strip()
    if not jwks_url:
        raise jwt.InvalidTokenError("IAM JWKS URL or public key PEM required")
    signing_key = _jwks_client(jwks_url).get_signing_key_from_jwt(raw_token)
    return jwt.decode(
        raw_token,
        signing_key.key,
        algorithms=["RS256"],
        audience=audience,
        issuer=issuer,
        options=opts,
    )


def _perm_list(payload: dict[str, Any]) -> list[str]:
    raw = payload.get("perm")
    if not isinstance(raw, list):
        return []
    return [str(x) for x in raw]


def _iam_perm_to_role(perm: list[str]) -> RoleName:
    p = set(perm)
    if "devault.platform.admin" in p:
        return "admin"
    if "devault.console.admin" in p:
        return "admin"
    if "devault.console.write" in p or "devault.control.write" in p:
        return "operator"
    return "auditor"


def _tenant_ids_from_payload(payload: dict[str, Any]) -> frozenset[uuid.UUID]:
    ids: list[uuid.UUID] = []
    tid = payload.get("tid")
    if tid is not None and str(tid).strip():
        ids.append(uuid.UUID(str(tid)))
    for x in payload.get("tids") or []:
        u = uuid.UUID(str(x))
        if u not in ids:
            ids.append(u)
    return frozenset(ids)


def auth_context_from_iam_payload(payload: dict[str, Any]) -> AuthContext:
    perm = _perm_list(payload)
    perm_f = frozenset(perm)
    pk = str(payload.get("pk") or "")
    sub = str(payload["sub"])
    mfa_ok = bool(payload.get("mfa", True))

    if sub.startswith("api_key:") or pk == "api_key":
        role = _iam_perm_to_role(perm)
        tid_set = _tenant_ids_from_payload(payload)
        allowed: frozenset[uuid.UUID] | None = None if not tid_set else tid_set
        return AuthContext(
            role=role,
            allowed_tenant_ids=allowed,
            principal_label=f"iam:{sub}",
            principal_kind="platform",
            user_id=None,
            mfa_satisfied=True,
            iam_perm=perm_f,
        )

    if pk == "platform" or "devault.platform.admin" in perm_f:
        return AuthContext(
            role="admin",
            allowed_tenant_ids=None,
            principal_label=f"iam:platform:{sub}",
            principal_kind="platform",
            user_id=None,
            mfa_satisfied=mfa_ok,
            iam_perm=perm_f,
        )

    uid = uuid.UUID(sub)
    tid_set = _tenant_ids_from_payload(payload)
    role = _iam_perm_to_role(perm)
    return AuthContext(
        role=role,
        allowed_tenant_ids=tid_set if tid_set else frozenset(),
        principal_label=f"iam:user:{uid}",
        principal_kind="tenant_user",
        user_id=uid,
        mfa_satisfied=mfa_ok,
        iam_perm=perm_f,
    )


def try_decode_iam_bearer(raw_token: str, settings: Settings) -> AuthContext | None:
    """Validate IAM-issued access JWT and map to :class:`AuthContext` (P5 / external IAM)."""
    if not iam_jwt_configured(settings):
        return None
    if raw_token.count(".") != 2:
        return None
    try:
        payload = decode_iam_access_token(raw_token, settings)
    except Exception:
        logger.debug("IAM JWT decode failed", exc_info=True)
        return None
    try:
        return auth_context_from_iam_payload(payload)
    except Exception:
        logger.debug("IAM JWT to auth context failed", exc_info=True)
        return None
