"""Shared path existence/readability checks for ``path_precheck`` jobs (Agent + tests)."""

from __future__ import annotations

import os


def path_precheck_report(paths: list[str]) -> tuple[bool, dict]:
    """Return (all_ok, report_dict) with schema ``devault-path-precheck-report-v1``."""
    rows: list[dict] = []
    ok_all = True
    for p in paths:
        ps = str(p).strip()
        exists = bool(ps) and os.path.exists(ps)
        readable = exists and os.access(ps, os.R_OK)
        rows.append({"path": ps, "exists": exists, "readable": readable})
        if not exists or not readable:
            ok_all = False
    return ok_all, {
        "schema": "devault-path-precheck-report-v1",
        "paths": rows,
    }
