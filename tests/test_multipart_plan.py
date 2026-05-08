from __future__ import annotations

from devault.storage.multipart import (
    effective_part_size_bytes,
    multipart_upload_is_complete,
    part_count,
)


def test_effective_part_size_caps_part_count() -> None:
    # 20 GiB with 16 MiB desired would exceed 10k parts; must grow part size.
    twenty_gib = 20 * 1024 * 1024 * 1024
    ps = effective_part_size_bytes(twenty_gib, 16 * 1024 * 1024)
    assert part_count(twenty_gib, ps) <= 10_000
    assert ps >= 5 * 1024 * 1024


def test_small_object_single_part_plan() -> None:
    size = 8 * 1024 * 1024
    ps = effective_part_size_bytes(size, 16 * 1024 * 1024)
    assert part_count(size, ps) == 1


def test_multipart_upload_is_complete_three_parts() -> None:
    size = 10 * 1024 * 1024 + 1
    cfg = 5 * 1024 * 1024
    uploaded = [
        {"PartNumber": 1, "ETag": '"a"'},
        {"PartNumber": 2, "ETag": '"b"'},
        {"PartNumber": 3, "ETag": '"c"'},
    ]
    assert multipart_upload_is_complete(
        content_length=size, configured_part_size=cfg, uploaded=uploaded
    )


def test_multipart_upload_is_complete_incomplete() -> None:
    size = 10 * 1024 * 1024 + 1
    cfg = 5 * 1024 * 1024
    uploaded = [{"PartNumber": 1, "ETag": '"a"'}]
    assert not multipart_upload_is_complete(
        content_length=size, configured_part_size=cfg, uploaded=uploaded
    )
