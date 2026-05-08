"""S3 multipart upload planning for large backup bundles (control plane + Agent presigned parts)."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from devault.storage.presign import presign_upload_part

if TYPE_CHECKING:
    from botocore.client import BaseClient


def start_multipart_upload(client: "BaseClient", *, bucket: str, key: str) -> str:
    resp = client.create_multipart_upload(Bucket=bucket, Key=key)
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
