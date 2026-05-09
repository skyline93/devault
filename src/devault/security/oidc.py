from __future__ import annotations

import functools
import logging
import uuid
from typing import Any

import httpx
import jwt
from jwt import PyJWKClient

from devault.security.auth_context import AuthContext, RoleName
from devault.settings import Settings

logger = logging.getLogger(__name__)


@functools.lru_cache(maxsize=8)
def _jwks_client(jwks_uri: str) -> PyJWKClient:
    return PyJWKClient(jwks_uri, cache_keys=True)


@functools.lru_cache(maxsize=8)
def _issuer_metadata(issuer: str) -> dict[str, Any]:
    issuer = issuer.rstrip("/")
    url = f"{issuer}/.well-known/openid-configuration"
    with httpx.Client(timeout=15.0) as client:
        r = client.get(url)
        r.raise_for_status()
        return r.json()


def try_decode_oidc_bearer(raw_token: str, settings: Settings) -> AuthContext | None:
    """If OIDC is configured and token is a JWT, validate and map claims to AuthContext."""
    issuer = (settings.oidc_issuer or "").strip().rstrip("/")
    audience = (settings.oidc_audience or "").strip()
    if not issuer or not audience:
        return None
    parts = raw_token.split(".")
    if len(parts) != 3:
        return None
    try:
        meta = _issuer_metadata(issuer)
        jwks_uri = str(meta.get("jwks_uri") or "")
        if not jwks_uri:
            logger.warning("OIDC discovery missing jwks_uri for issuer %s", issuer)
            return None
        signing_key = _jwks_client(jwks_uri).get_signing_key_from_jwt(raw_token)
        claims = jwt.decode(
            raw_token,
            signing_key.key,
            algorithms=["RS256", "ES256", "EdDSA"],
            audience=audience,
            issuer=issuer,
            options={"require": ["exp", "iat"]},
        )
    except Exception as e:
        logger.debug("OIDC JWT decode failed: %s", e)
        return None

    role_raw = claims.get(settings.oidc_role_claim) or claims.get("devault_role")
    if isinstance(role_raw, list) and role_raw:
        role_raw = role_raw[0]
    if not isinstance(role_raw, str):
        return None
    role_s = role_raw.strip().lower()
    if role_s not in ("admin", "operator", "auditor"):
        logger.warning("OIDC token has unsupported role claim %r", role_raw)
        return None
    role: RoleName = role_s  # type: ignore[assignment]

    sub = str(claims.get("sub") or "oidc-user")
    label = f"oidc:{sub}"

    allowed: frozenset[uuid.UUID] | None = None
    if role == "admin":
        allowed = None
    else:
        tid_claim = settings.oidc_tenant_ids_claim
        raw_ids = claims.get(tid_claim) if tid_claim else claims.get("devault_tenant_ids")
        if raw_ids is None:
            allowed = frozenset()
        elif isinstance(raw_ids, str):
            allowed = frozenset(uuid.UUID(x.strip()) for x in raw_ids.split(",") if x.strip())
        elif isinstance(raw_ids, list):
            allowed = frozenset(uuid.UUID(str(x)) for x in raw_ids)
        else:
            allowed = frozenset()

    return AuthContext(role=role, allowed_tenant_ids=allowed, principal_label=label)
