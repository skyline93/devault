from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from devault.db.models import Tenant
from devault.security.iam_jwt import auth_context_from_iam_payload, try_decode_iam_bearer
from devault.services.auth_session_payload import build_auth_session_out
from devault.settings import Settings


def _rsa_keypair() -> tuple[bytes, bytes]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return priv, pub


def _settings_iam(pub_pem: bytes) -> Settings:
    return Settings(
        iam_jwt_public_key_pem=pub_pem.decode(),
        iam_jwt_issuer="http://iam.test",
        iam_jwt_audience="devault-api",
    )


def test_try_decode_iam_bearer_human_operator() -> None:
    priv, pub = _rsa_keypair()
    settings = _settings_iam(pub)
    uid = uuid.uuid4()
    tid = uuid.uuid4()
    now = datetime.now(timezone.utc)
    tok = jwt.encode(
        {
            "sub": str(uid),
            "iss": settings.iam_jwt_issuer,
            "aud": settings.iam_jwt_audience,
            "iat": now,
            "exp": now + timedelta(minutes=10),
            "perm": ["devault.console.write", "devault.control.read"],
            "pk": "tenant_user",
            "mfa": True,
            "tid": str(tid),
            "tids": [str(tid)],
        },
        priv,
        algorithm="RS256",
        headers={"kid": "k1"},
    )
    ctx = try_decode_iam_bearer(tok, settings)
    assert ctx is not None
    assert ctx.principal_label == f"iam:user:{uid}"
    assert ctx.user_id == uid
    assert ctx.role == "operator"
    assert tid in (ctx.allowed_tenant_ids or frozenset())


def test_auth_context_platform_admin() -> None:
    uid = uuid.uuid4()
    payload = {
        "sub": str(uid),
        "perm": ["devault.platform.admin", "devault.console.admin"],
        "pk": "platform",
        "mfa": True,
    }
    ctx = auth_context_from_iam_payload(payload)
    assert ctx.principal_kind == "platform"
    assert ctx.allowed_tenant_ids is None
    assert ctx.role == "admin"


def test_build_session_iam_human_uses_tenant_rows() -> None:
    tid = uuid.uuid4()
    uid = uuid.uuid4()
    auth = auth_context_from_iam_payload(
        {
            "sub": str(uid),
            "perm": ["devault.console.read"],
            "pk": "tenant_user",
            "mfa": True,
            "tid": str(tid),
            "tids": [str(tid)],
        }
    )
    db = MagicMock()

    def _get(model: type, pk: uuid.UUID) -> object | None:
        if model is Tenant and pk == tid:
            return SimpleNamespace(
                id=tid,
                name="IAM Sync",
                slug="iam-sync",
                require_mfa_for_admins=False,
                sso_password_login_disabled=False,
            )
        return None

    db.get.side_effect = _get
    out = build_auth_session_out(auth, db)
    assert out.user_id == uid
    assert out.email is None
    assert out.tenants and out.tenants[0].tenant_id == tid
