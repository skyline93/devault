from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import boto3
import pytest

from devault.settings import Settings
from devault.storage.s3_client import (
    S3ConnSpec,
    build_s3_client_from_spec,
    reset_assume_role_credential_cache,
)


@pytest.fixture(autouse=True)
def _clear_assume_role_cache() -> None:
    reset_assume_role_credential_cache()
    yield
    reset_assume_role_credential_cache()


def _base_settings(**kwargs: object) -> Settings:
    defaults: dict = {
        "database_url": "postgresql+psycopg://localhost/devault",
        "redis_url": "redis://localhost:6379/0",
        "aws_default_region": "us-east-1",
    }
    defaults.update(kwargs)
    return Settings(**defaults)


def test_build_s3_client_from_spec_uses_static_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}
    s3_mock = MagicMock()

    def fake_client(self: object, service_name: str, **kwargs: object) -> MagicMock:
        if service_name == "s3":
            captured.update(kwargs)
            return s3_mock
        raise AssertionError(service_name)

    monkeypatch.setattr(boto3.session.Session, "client", fake_client)
    s = _base_settings()
    spec = S3ConnSpec(
        endpoint="https://s3.example.com",
        region="us-east-1",
        use_ssl=True,
        bucket="b",
        access_key="AKIA_TEST",
        secret_key="secret",
        assume_role_arn=None,
        assume_role_external_id=None,
    )
    c = build_s3_client_from_spec(s, spec)
    assert c is s3_mock
    assert captured["aws_access_key_id"] == "AKIA_TEST"
    assert captured["aws_secret_access_key"] == "secret"
    assert "aws_session_token" not in captured


def test_build_s3_client_from_spec_assume_role_then_s3(monkeypatch: pytest.MonkeyPatch) -> None:
    sts = MagicMock()
    sts.assume_role.return_value = {
        "Credentials": {
            "AccessKeyId": "ASIA",
            "SecretAccessKey": "tempsecret",
            "SessionToken": "token",
            "Expiration": datetime.now(timezone.utc) + timedelta(hours=1),
        }
    }
    s3 = MagicMock()
    order: list[str] = []

    def fake_client(self: object, service_name: str, **kwargs: object) -> MagicMock:
        order.append(service_name)
        if service_name == "sts":
            assert kwargs.get("region_name") == "eu-west-1"
            return sts
        if service_name == "s3":
            assert kwargs["aws_access_key_id"] == "ASIA"
            assert kwargs["aws_session_token"] == "token"
            return s3
        raise AssertionError(service_name)

    monkeypatch.setattr(boto3.session.Session, "client", fake_client)
    s = _base_settings(
        aws_default_region="eu-west-1",
        s3_assume_role_session_name="session-x",
    )
    spec = S3ConnSpec(
        endpoint="https://s3.example.com",
        region="eu-west-1",
        use_ssl=True,
        bucket="b",
        access_key=None,
        secret_key=None,
        assume_role_arn="arn:aws:iam::111111111111:role/devault-s3",
        assume_role_external_id=None,
    )
    c = build_s3_client_from_spec(s, spec)
    assert c is s3
    sts.assume_role.assert_called_once()
    ar_kw = sts.assume_role.call_args.kwargs
    assert ar_kw["RoleArn"] == "arn:aws:iam::111111111111:role/devault-s3"
    assert ar_kw["RoleSessionName"] == "session-x"
    assert order == ["sts", "s3"]


def test_assume_role_credentials_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    sts = MagicMock()
    sts.assume_role.return_value = {
        "Credentials": {
            "AccessKeyId": "ASIA",
            "SecretAccessKey": "tempsecret",
            "SessionToken": "token",
            "Expiration": datetime.now(timezone.utc) + timedelta(hours=1),
        }
    }

    def fake_client(self: object, service_name: str, **kwargs: object) -> MagicMock:
        if service_name == "sts":
            return sts
        if service_name == "s3":
            return MagicMock()
        raise AssertionError(service_name)

    monkeypatch.setattr(boto3.session.Session, "client", fake_client)
    s = _base_settings(aws_default_region="us-east-1")
    spec = S3ConnSpec(
        endpoint="https://s3.amazonaws.com",
        region="us-east-1",
        use_ssl=True,
        bucket="b",
        access_key=None,
        secret_key=None,
        assume_role_arn="arn:aws:iam::1:role/r",
        assume_role_external_id=None,
    )
    build_s3_client_from_spec(s, spec)
    build_s3_client_from_spec(s, spec)
    assert sts.assume_role.call_count == 1
