from __future__ import annotations

import boto3
from botocore.client import BaseClient

from devault.settings import Settings


def s3_client_from_settings(settings: Settings) -> BaseClient:
    if not settings.s3_access_key or not settings.s3_secret_key:
        raise RuntimeError("S3 presign requires DEVAULT_S3_ACCESS_KEY and DEVAULT_S3_SECRET_KEY")
    session = boto3.session.Session()
    return session.client(
        "s3",
        endpoint_url=settings.s3_endpoint or None,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        use_ssl=settings.s3_use_ssl,
    )


def presign_put_object(
    client: BaseClient,
    *,
    bucket: str,
    key: str,
    expires_in: int,
) -> str:
    return client.generate_presigned_url(
        "put_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires_in,
        HttpMethod="PUT",
    )


def presign_get_object(
    client: BaseClient,
    *,
    bucket: str,
    key: str,
    expires_in: int,
) -> str:
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires_in,
    )


def presign_upload_part(
    client: BaseClient,
    *,
    bucket: str,
    key: str,
    upload_id: str,
    part_number: int,
    expires_in: int,
) -> str:
    return client.generate_presigned_url(
        "upload_part",
        Params={
            "Bucket": bucket,
            "Key": key,
            "UploadId": upload_id,
            "PartNumber": part_number,
        },
        ExpiresIn=expires_in,
        HttpMethod="PUT",
    )
