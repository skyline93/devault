"""Build boto3 S3 clients for the control plane: static keys, AssumeRole, or default chain."""

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


def _assume_role_cache_key(settings: Settings) -> str:
    return "|".join(
        [
            settings.s3_assume_role_arn or "",
            settings.s3_assume_role_external_id or "",
            settings.s3_assume_role_session_name,
            str(settings.s3_assume_role_duration_seconds),
            settings.s3_sts_region or settings.s3_region,
            settings.s3_sts_endpoint_url or "",
            settings.s3_access_key or "",
            settings.s3_secret_key or "",
        ]
    )


def _session_kwargs_for_base_chain(settings: Settings) -> dict[str, Any]:
    if settings.s3_access_key and settings.s3_secret_key:
        return {
            "aws_access_key_id": settings.s3_access_key,
            "aws_secret_access_key": settings.s3_secret_key,
        }
    return {}


def _fetch_assume_role_credentials(settings: Settings) -> _CachedAssumeRole:
    if not settings.s3_assume_role_arn:
        raise RuntimeError("s3_assume_role_arn required for AssumeRole credential path")

    session = boto3.session.Session(**_session_kwargs_for_base_chain(settings))
    sts_region = settings.s3_sts_region or settings.s3_region
    sts_kwargs: dict[str, Any] = {
        "region_name": sts_region,
        "use_ssl": settings.s3_sts_use_ssl,
    }
    if settings.s3_sts_endpoint_url:
        sts_kwargs["endpoint_url"] = settings.s3_sts_endpoint_url

    sts = session.client("sts", **sts_kwargs)
    params: dict[str, Any] = {
        "RoleArn": settings.s3_assume_role_arn,
        "RoleSessionName": settings.s3_assume_role_session_name[:64],
        "DurationSeconds": settings.s3_assume_role_duration_seconds,
    }
    if settings.s3_assume_role_external_id:
        params["ExternalId"] = settings.s3_assume_role_external_id

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


def _credentials_for_s3(settings: Settings) -> dict[str, Any]:
    """Return kwargs for boto3 Session().client('s3', **credentials, ...)."""
    if settings.s3_assume_role_arn:
        key = _assume_role_cache_key(settings)
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
            fresh = _fetch_assume_role_credentials(settings)
            _ASSUME_ROLE_CACHE[key] = fresh
        return {
            "aws_access_key_id": fresh.access_key_id,
            "aws_secret_access_key": fresh.secret_access_key,
            "aws_session_token": fresh.session_token,
        }

    if settings.s3_access_key and settings.s3_secret_key:
        return {
            "aws_access_key_id": settings.s3_access_key,
            "aws_secret_access_key": settings.s3_secret_key,
        }

    return {}


def build_s3_client(settings: Settings) -> BaseClient:
    """
    Control-plane S3 client for presigning, multipart control APIs, and existence checks.

    Resolution order when ``DEVAULT_STORAGE_BACKEND=s3``:

    1. If ``DEVAULT_S3_ASSUME_ROLE_ARN`` is set: call STS ``AssumeRole`` using either
       static ``DEVAULT_S3_ACCESS_KEY`` / ``DEVAULT_S3_SECRET_KEY`` (optional) or the
       process default credential chain (IRSA, instance profile, env), then build S3
       with the returned temporary keys. Credentials are cached until shortly before expiry.
    2. Else if static keys are set: S3 client with those keys.
    3. Else: S3 client using the default credential chain only (no AssumeRole).
    """
    creds = _credentials_for_s3(settings)
    session = boto3.session.Session()
    return session.client(
        "s3",
        endpoint_url=settings.s3_endpoint or None,
        region_name=settings.s3_region,
        use_ssl=settings.s3_use_ssl,
        **creds,
    )


def s3_client_from_settings(settings: Settings) -> BaseClient:
    """Backward-compatible alias used by gRPC servicer and presign helpers."""
    return build_s3_client(settings)
