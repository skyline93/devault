#!/usr/bin/env python3
"""Emit GitHub Actions matrix JSON for e2e-version-matrix workflow from docs/compatibility.json."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
COMPAT = REPO / "docs" / "compatibility.json"


def build_rows(github_sha: str, previous_minor_git_ref: str) -> list[dict[str, str]]:
    sha = (github_sha or "").strip()
    if not sha:
        raise ValueError("GITHUB_SHA is required")
    prev = (previous_minor_git_ref or "").strip()
    rows: list[dict[str, str]] = [
        {
            "id": "homogeneous",
            "cp_ref": sha,
            "agent_ref": sha,
        }
    ]
    if prev:
        rows.append(
            {
                "id": "cp_current_agent_prev_minor",
                "cp_ref": sha,
                "agent_ref": prev,
            }
        )
        rows.append(
            {
                "id": "cp_prev_minor_agent_current",
                "cp_ref": prev,
                "agent_ref": sha,
            }
        )
    return rows


def main() -> int:
    data = json.loads(COMPAT.read_text(encoding="utf-8"))
    e2e = data.get("ci_e2e") or {}
    prev = str(e2e.get("previous_minor_git_ref") or "")
    sha = os.environ.get("GITHUB_SHA", "").strip()
    if not sha:
        print("error: GITHUB_SHA unset (required in CI)", file=sys.stderr)
        return 1
    rows = build_rows(sha, prev)
    payload = json.dumps({"include": rows}, separators=(",", ":"))
    out_path = os.environ.get("GITHUB_OUTPUT")
    if out_path:
        with open(out_path, "a", encoding="utf-8") as fh:
            fh.write(f"matrix={payload}\n")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
