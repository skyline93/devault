"""Policy path merge/split for allowlist checkboxes + extra textarea（`policy_paths_form_merge`）。"""

from __future__ import annotations

from devault.services.policy_paths_form_merge import (
    merge_policy_paths_from_allowlist_form,
    split_policy_paths_for_allowlist_form,
)


def test_merge_union_order_then_extras_dedupe() -> None:
    union = ["/mnt/a", "/data"]
    out = merge_policy_paths_from_allowlist_form(
        allowlist_union=union,
        paths_from_allowlist=["/data", "/mnt/a"],
        paths_extra_multiline="/data/sub\n/mnt/a",
    )
    assert out == ["/mnt/a", "/data", "/data/sub"]


def test_merge_ignores_unknown_checkbox_values() -> None:
    out = merge_policy_paths_from_allowlist_form(
        allowlist_union=["/x"],
        paths_from_allowlist=["/x", "/evil"],
        paths_extra_multiline="",
    )
    assert out == ["/x"]


def test_split_exact_union_vs_extra() -> None:
    sel, extra = split_policy_paths_for_allowlist_form(
        ["/data/app", "/data", "/other"],
        ["/data", "/mnt"],
    )
    assert sel == ["/data"]
    assert extra == "/data/app\n/other"
