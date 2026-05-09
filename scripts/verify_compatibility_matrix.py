#!/usr/bin/env python3
"""Validate ``docs/compatibility.json`` against ``pyproject.toml`` and server capability registry."""

from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def verify() -> int:
    doc_path = REPO / "docs" / "compatibility.json"
    if not doc_path.is_file():
        print(f"error: missing {doc_path}", file=sys.stderr)
        return 1
    data = json.loads(doc_path.read_text(encoding="utf-8"))
    if int(data.get("schema_version", 0)) < 1:
        print("error: compatibility.json schema_version missing or invalid", file=sys.stderr)
        return 1

    py_ver = str(
        tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    )
    cur = data.get("current") or {}
    doc_ver = cur.get("control_plane_release")
    if doc_ver != py_ver:
        print(
            f"error: docs/compatibility.json current.control_plane_release={doc_ver!r} "
            f"!= pyproject.toml version={py_ver!r}",
            file=sys.stderr,
        )
        return 1

    from devault.release_meta import GRPC_API_PACKAGE

    grpc_block = data.get("grpc") or {}
    if grpc_block.get("package") != GRPC_API_PACKAGE:
        print(
            f"error: compatibility.json grpc.package={grpc_block.get('package')!r} "
            f"!= {GRPC_API_PACKAGE!r}",
            file=sys.stderr,
        )
        return 1

    known = tuple(grpc_block.get("known_capabilities") or [])
    from devault.server_capabilities import ALL_KNOWN_SERVER_CAPABILITIES

    if tuple(sorted(known)) != tuple(sorted(ALL_KNOWN_SERVER_CAPABILITIES)):
        print(
            "error: grpc.known_capabilities must exactly match "
            "devault.server_capabilities.ALL_KNOWN_SERVER_CAPABILITIES "
            f"(json={sorted(known)!r} code={sorted(ALL_KNOWN_SERVER_CAPABILITIES)!r})",
            file=sys.stderr,
        )
        return 1

    mats = data.get("matrices")
    if not isinstance(mats, list) or not mats:
        print("error: matrices must be a non-empty list", file=sys.stderr)
        return 1
    for i, row in enumerate(mats):
        if not isinstance(row, dict):
            print(f"error: matrices[{i}] must be an object", file=sys.stderr)
            return 1
        for k in ("id", "control_plane", "agent_release"):
            if k not in row:
                print(f"error: matrices[{i}] missing required key {k!r}", file=sys.stderr)
                return 1

    print("ok: compatibility.json ↔ release metadata")
    return 0


if __name__ == "__main__":
    raise SystemExit(verify())
