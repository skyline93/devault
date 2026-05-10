from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from jwt.algorithms import RSAAlgorithm

from devault_iam.settings import Settings


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    """JWT access claims. ``sub`` is user UUID string or ``api_key:{uuid}``."""

    sub: str
    tid: uuid.UUID | None
    tids: list[uuid.UUID]
    perm: list[str]
    pk: str  # tenant_user | platform | api_key
    mfa: bool


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def issue_access_token(
    *,
    private_key_pem: str,
    settings: Settings,
    claims: AccessTokenClaims,
    ttl_seconds: int,
) -> str:
    now = _utcnow()
    payload: dict[str, Any] = {
        "sub": claims.sub,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now,
        "exp": now + timedelta(seconds=ttl_seconds),
        "jti": str(uuid.uuid4()),
        "perm": claims.perm,
        "pk": claims.pk,
        "mfa": claims.mfa,
    }
    if claims.tid is not None:
        payload["tid"] = str(claims.tid)
    if claims.tids:
        payload["tids"] = [str(x) for x in claims.tids]
    return jwt.encode(
        payload,
        private_key_pem,
        algorithm="RS256",
        headers={"kid": settings.jwt_key_id, "typ": "JWT"},
    )


def decode_access_token(
    *,
    token: str,
    public_key_pem: str,
    settings: Settings,
) -> dict[str, Any]:
    return jwt.decode(
        token,
        public_key_pem,
        algorithms=["RS256"],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
        options={"require": ["exp", "iat", "sub", "aud", "iss"]},
    )


def public_pem_to_jwks(public_key_pem: str, kid: str) -> dict[str, Any]:
    pub = serialization.load_pem_public_key(
        public_key_pem.encode("utf-8"),
        backend=default_backend(),
    )
    data = RSAAlgorithm.to_jwk(pub, as_dict=True)
    data["kid"] = kid
    data["use"] = "sig"
    data["alg"] = "RS256"
    return {"keys": [data]}
