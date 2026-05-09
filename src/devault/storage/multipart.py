"""S3 multipart upload planning for large backup bundles (control plane + Agent presigned parts)."""

from __future__ import annotations

import math
from datetime import datetime
from typing import TYPE_CHECKING, Any

from devault.storage.presign import presign_upload_part

if TYPE_CHECKING:
    from botocore.client import BaseClient


def start_multipart_upload(
    client: "BaseClient",
    *,
    bucket: str,
    key: str,
    object_lock_mode: str | None = None,
    object_lock_retain_until: datetime | None = None,
) -> str:
    kwargs: dict[str, Any] = {"Bucket": bucket, "Key": key}
    if object_lock_mode and object_lock_retain_until:
        kwargs["ObjectLockMode"] = object_lock_mode
        kwargs["ObjectLockRetainUntilDate"] = object_lock_retain_until
    resp = client.create_multipart_upload(**kwargs)
    return str(resp["UploadId"])

# S3 allows at most 10,000 parts per multipart upload.
_MAX_PARTS = 10_000
_MIN_PART = 5 * 1024 * 1024


def effective_part_size_bytes(
    content_length: int,
    desired_part_size: int,
    *,
    max_parts: int = _MAX_PARTS,
) -> int:
    """Raise part size if needed so part count stays within S3 limits."""
    if content_length <= 0:
        raise ValueError("content_length must be positive")
    ps = max(int(desired_part_size), _MIN_PART)
    while math.ceil(content_length / ps) > max_parts:
        ps = max(math.ceil(content_length / max_parts), _MIN_PART)
    return ps


def part_count(content_length: int, part_size: int) -> int:
    return max(1, math.ceil(content_length / part_size))


def multipart_upload_is_complete(
    *,
    content_length: int,
    configured_part_size: int,
    uploaded: list[dict[str, object]],
) -> bool:
    """True when S3 ListParts covers every expected part number for this object size."""
    eff_ps = effective_part_size_bytes(content_length, configured_part_size)
    n = part_count(content_length, eff_ps)
    have = {int(x["PartNumber"]) for x in uploaded}
    return have == set(range(1, n + 1))


def build_multipart_part_presigns(
    client: "BaseClient",
    *,
    bucket: str,
    key: str,
    upload_id: str,
    content_length: int,
    part_size: int,
    expires_in: int,
) -> list[tuple[int, str]]:
    """Return (part_number, presigned_put_url) for each part (1-based part numbers)."""
    ps = effective_part_size_bytes(content_length, part_size)
    n = part_count(content_length, ps)
    out: list[tuple[int, str]] = []
    for pn in range(1, n + 1):
        url = presign_upload_part(
            client,
            bucket=bucket,
            key=key,
            upload_id=upload_id,
            part_number=pn,
            expires_in=expires_in,
        )
        out.append((pn, url))
    return out


def list_uploaded_multipart_parts(
    client: "BaseClient",
    *,
    bucket: str,
    key: str,
    upload_id: str,
) -> list[dict[str, object]]:
    """Return S3 ListParts entries as dicts with PartNumber (int) and ETag (str, quoted)."""
    out: list[dict[str, object]] = []
    paginator = client.get_paginator("list_parts")
    for page in paginator.paginate(Bucket=bucket, Key=key, UploadId=upload_id):
        for p in page.get("Parts", []) or []:
            out.append(
                {
                    "PartNumber": int(p["PartNumber"]),
                    "ETag": str(p["ETag"]),
                }
            )
    out.sort(key=lambda x: int(x["PartNumber"]))
    return out


def abort_multipart_upload_best_effort(
    client: "BaseClient",
    *,
    bucket: str,
    key: str,
    upload_id: str,
) -> None:
    """Abort an in-flight multipart upload; ignore missing / already completed."""
    try:
        client.abort_multipart_upload(Bucket=bucket, Key=key, UploadId=upload_id)
    except Exception:
        pass


def build_multipart_part_presigns_missing(
    client: "BaseClient",
    *,
    bucket: str,
    key: str,
    upload_id: str,
    content_length: int,
    part_size: int,
    expires_in: int,
    skip_part_numbers: set[int],
) -> list[tuple[int, str]]:
    """Presign only parts not yet uploaded (by part number)."""
    ps = effective_part_size_bytes(content_length, part_size)
    n = part_count(content_length, ps)
    out: list[tuple[int, str]] = []
    for pn in range(1, n + 1):
        if pn in skip_part_numbers:
            continue
        url = presign_upload_part(
            client,
            bucket=bucket,
            key=key,
            upload_id=upload_id,
            part_number=pn,
            expires_in=expires_in,
        )
        out.append((pn, url))
    return out
