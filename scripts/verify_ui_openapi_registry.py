#!/usr/bin/env python3
"""Fail if key OpenAPI-facing fields are missing from Web UI templates (§十四-17 gate)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TPL = ROOT / "src" / "devault" / "web" / "templates"

CHECKS: list[tuple[str, Path, tuple[str, ...]]] = [
    (
        "jobs.html",
        TPL / "jobs.html",
        ("lease_agent_id", "lease_agent_hostname", "completed_agent_hostname", "auth_ctx.can_write()"),
    ),
    (
        "policies.html",
        TPL / "policies.html",
        ("bound_agent_id", "bound_agent_pool_id", "updated_at", "auth_ctx.can_write()"),
    ),
]


def main() -> int:
    failed = False
    for label, path, needles in CHECKS:
        if not path.is_file():
            print(f"missing template {path}", file=sys.stderr)
            failed = True
            continue
        text = path.read_text(encoding="utf-8")
        for n in needles:
            if n not in text:
                print(f"{label}: expected substring {n!r} not found", file=sys.stderr)
                failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
