from __future__ import annotations

from botocore.client import BaseClient

from devault.storage.s3_client import s3_client_from_settings

__all__ = [
    "presign_get_object",
    "presign_put_object",
    "presign_upload_part",
    "s3_client_from_settings",
]


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
