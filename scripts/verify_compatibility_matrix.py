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

    matrix_ids = {str(m["id"]) for m in mats if isinstance(m, dict) and "id" in m}
    e2e = data.get("ci_e2e")
    if e2e is not None:
        if not isinstance(e2e, dict):
            print("error: ci_e2e must be an object when present", file=sys.stderr)
            return 1
        prev = e2e.get("previous_minor_git_ref", "")
        if not isinstance(prev, str):
            print("error: ci_e2e.previous_minor_git_ref must be a string", file=sys.stderr)
            return 1
        wf = e2e.get("workflow")
        if wf is not None:
            if not isinstance(wf, str) or not wf.strip():
                print("error: ci_e2e.workflow must be a non-empty string when set", file=sys.stderr)
                return 1
            wf_path = REPO / wf
            if not wf_path.is_file():
                print(f"error: ci_e2e.workflow points to missing file {wf_path}", file=sys.stderr)
                return 1
        defs = e2e.get("matrix_definitions")
        if defs is not None:
            if not isinstance(defs, list) or not defs:
                print("error: ci_e2e.matrix_definitions must be a non-empty list when set", file=sys.stderr)
                return 1
            for j, d in enumerate(defs):
                if not isinstance(d, dict):
                    print(f"error: ci_e2e.matrix_definitions[{j}] must be an object", file=sys.stderr)
                    return 1
                for req in ("matrix_job_id", "control_plane_git_ref", "agent_git_ref", "maps_to_compatibility_rows"):
                    if req not in d:
                        print(
                            f"error: ci_e2e.matrix_definitions[{j}] missing required key {req!r}",
                            file=sys.stderr,
                        )
                        return 1
                maps = d["maps_to_compatibility_rows"]
                if not isinstance(maps, list) or not maps:
                    print(
                        f"error: ci_e2e.matrix_definitions[{j}].maps_to_compatibility_rows must be a non-empty list",
                        file=sys.stderr,
                    )
                    return 1
                for mid in maps:
                    if str(mid) not in matrix_ids:
                        print(
                            f"error: ci_e2e.matrix_definitions[{j}] references unknown matrices.id {mid!r}",
                            file=sys.stderr,
                        )
                        return 1

    print("ok: compatibility.json ↔ release metadata")
    return 0


if __name__ == "__main__":
    raise SystemExit(verify())
