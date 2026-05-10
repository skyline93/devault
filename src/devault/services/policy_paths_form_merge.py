"""Merge/split policy paths for allowlist checkboxes + extra textarea (原 Jinja UI 逻辑，供测试与将来复用)."""

from __future__ import annotations


def _lines(text: str | None) -> list[str]:
    return [ln.strip() for ln in (text or "").splitlines() if ln.strip()]


def _path_norm_key(path: str) -> str:
    s = path.strip()
    return s.rstrip("/") or "/"


def merge_policy_paths_from_allowlist_form(
    *,
    allowlist_union: list[str],
    paths_from_allowlist: list[str] | None,
    paths_extra_multiline: str,
) -> list[str]:
    """Allowlist checkboxes (validated against union) in union order, then extra lines; dedupe by normalized path."""
    submitted = {str(x).strip() for x in (paths_from_allowlist or [])}
    merged: list[str] = []
    seen: set[str] = set()
    for u in allowlist_union:
        uu = str(u).strip()
        if uu in submitted:
            k = _path_norm_key(uu)
            if k not in seen:
                seen.add(k)
                merged.append(uu)
    for line in _lines(paths_extra_multiline):
        k = _path_norm_key(line)
        if k not in seen:
            seen.add(k)
            merged.append(line)
    return merged


def split_policy_paths_for_allowlist_form(
    policy_paths: list[str],
    allowlist_union: list[str],
) -> tuple[list[str], str]:
    """Paths that exactly match a union root -> checkboxes; everything else -> extra textarea."""
    selected: list[str] = []
    extras: list[str] = []
    seen_sel: set[str] = set()
    for raw in policy_paths or []:
        line = raw.strip()
        if not line:
            continue
        line_key = _path_norm_key(line)
        matched: str | None = None
        for u in allowlist_union:
            uu = str(u).strip()
            if _path_norm_key(uu) == line_key:
                matched = uu
                break
        if matched is not None:
            mk = _path_norm_key(matched)
            if mk not in seen_sel:
                seen_sel.add(mk)
                selected.append(matched)
        else:
            extras.append(line)
    return selected, "\n".join(extras)
