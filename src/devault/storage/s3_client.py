"""Build boto3 S3 clients from a resolved connection spec (DB-backed storage profiles)."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import boto3
from botocore.client import BaseClient

from devault.settings import Settings

_CACHE_LOCK = threading.Lock()
_ASSUME_ROLE_CACHE: dict[str, _CachedAssumeRole] = {}


def reset_assume_role_credential_cache() -> None:
    """Clear cached STS credentials (for tests or hot config reload in rare setups)."""
    with _CACHE_LOCK:
        _ASSUME_ROLE_CACHE.clear()


@dataclass(frozen=True)
class _CachedAssumeRole:
    access_key_id: str
    secret_access_key: str
    session_token: str
    expires_at: datetime


@dataclass(frozen=True)
class S3ConnSpec:
    """Resolved S3-compatible endpoint and credentials for one storage profile."""

    endpoint: str | None
    region: str
    use_ssl: bool
    bucket: str
    access_key: str | None
    secret_key: str | None
    assume_role_arn: str | None
    assume_role_external_id: str | None


def _assume_role_cache_key(
    settings: Settings,
    spec: S3ConnSpec,
    *,
    role_arn: str,
    external_id: str | None,
) -> str:
    return "|".join(
        [
            role_arn,
            external_id or "",
            settings.s3_assume_role_session_name,
            str(settings.s3_assume_role_duration_seconds),
            settings.s3_sts_region or spec.region,
            settings.s3_sts_endpoint_url or "",
            spec.access_key or "",
            spec.secret_key or "",
        ]
    )


def _session_kwargs_for_base_chain(spec: S3ConnSpec) -> dict[str, Any]:
    if spec.access_key and spec.secret_key:
        return {
            "aws_access_key_id": spec.access_key,
            "aws_secret_access_key": spec.secret_key,
        }
    return {}


def _fetch_assume_role_credentials(
    settings: Settings,
    spec: S3ConnSpec,
    *,
    role_arn: str,
    external_id: str | None,
) -> _CachedAssumeRole:
    session = boto3.session.Session(**_session_kwargs_for_base_chain(spec))
    sts_region = settings.s3_sts_region or spec.region
    sts_kwargs: dict[str, Any] = {
        "region_name": sts_region,
        "use_ssl": settings.s3_sts_use_ssl,
    }
    if settings.s3_sts_endpoint_url:
        sts_kwargs["endpoint_url"] = settings.s3_sts_endpoint_url

    sts = session.client("sts", **sts_kwargs)
    params: dict[str, Any] = {
        "RoleArn": role_arn,
        "RoleSessionName": settings.s3_assume_role_session_name[:64],
        "DurationSeconds": settings.s3_assume_role_duration_seconds,
    }
    if external_id:
        params["ExternalId"] = external_id

    resp = sts.assume_role(**params)
    creds = resp["Credentials"]
    exp = creds["Expiration"]
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    return _CachedAssumeRole(
        access_key_id=creds["AccessKeyId"],
        secret_access_key=creds["SecretAccessKey"],
        session_token=creds["SessionToken"],
        expires_at=exp,
    )


def _credentials_for_spec(settings: Settings, spec: S3ConnSpec) -> dict[str, Any]:
    """Return kwargs for boto3 Session().client('s3', **credentials, ...)."""
    role_arn = spec.assume_role_arn
    if role_arn:
        key = _assume_role_cache_key(settings, spec, role_arn=role_arn, external_id=spec.assume_role_external_id)
        refresh_margin = timedelta(minutes=5)
        now = datetime.now(timezone.utc)
        with _CACHE_LOCK:
            cached = _ASSUME_ROLE_CACHE.get(key)
            if cached and cached.expires_at > now + refresh_margin:
                return {
                    "aws_access_key_id": cached.access_key_id,
                    "aws_secret_access_key": cached.secret_access_key,
                    "aws_session_token": cached.session_token,
                }
            fresh = _fetch_assume_role_credentials(
                settings,
                spec,
                role_arn=role_arn,
                external_id=spec.assume_role_external_id,
            )
            _ASSUME_ROLE_CACHE[key] = fresh
        return {
            "aws_access_key_id": fresh.access_key_id,
            "aws_secret_access_key": fresh.secret_access_key,
            "aws_session_token": fresh.session_token,
        }

    if spec.access_key and spec.secret_key:
        return {
            "aws_access_key_id": spec.access_key,
            "aws_secret_access_key": spec.secret_key,
        }

    return {}


def _make_s3_client(settings: Settings, spec: S3ConnSpec, creds: dict[str, Any]) -> BaseClient:
    session = boto3.session.Session()
    return session.client(
        "s3",
        endpoint_url=spec.endpoint or None,
        region_name=spec.region,
        use_ssl=spec.use_ssl,
        **creds,
    )


def build_s3_client_from_spec(settings: Settings, spec: S3ConnSpec) -> BaseClient:
    """
    Control-plane S3 client for presigning, multipart control APIs, and existence checks.

    Resolution order:

    1. If ``spec.assume_role_arn`` is set: STS ``AssumeRole`` using static keys from ``spec`` (if any)
       or the process default credential chain, then S3 with temporary keys (cached).
    2. Else if static keys on ``spec``: S3 client with those keys.
    3. Else: S3 client using the default credential chain only.
    """
    creds = _credentials_for_spec(settings, spec)
    return _make_s3_client(settings, spec, creds)


def s3_client_from_spec(settings: Settings, spec: S3ConnSpec) -> BaseClient:
    """Alias used by gRPC servicer and presign helpers."""
    return build_s3_client_from_spec(settings, spec)
