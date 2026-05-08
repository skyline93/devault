from __future__ import annotations

from devault.storage.multipart import effective_part_size_bytes, part_count


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
