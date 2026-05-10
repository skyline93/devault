#!/usr/bin/env python3
"""Emit FastAPI OpenAPI JSON for console codegen (十五-02)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def main() -> int:
    p = argparse.ArgumentParser(description="Write OpenAPI JSON from devault.api.main:app")
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        required=True,
        help="Output path (e.g. console/openapi.json)",
    )
    args = p.parse_args()
    from devault.api.main import app  # noqa: PLC0415

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(app.openapi(), indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
