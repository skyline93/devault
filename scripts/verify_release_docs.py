#!/usr/bin/env python3
"""Fail if ``CHANGELOG.md`` has no section heading for the current ``pyproject.toml`` version."""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    pyproject = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))
    version = str(pyproject["project"]["version"])
    changelog = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
    marker = f"## [{version}]"
    if marker not in changelog:
        print(
            f"error: CHANGELOG.md must contain a release section {marker!r} "
            f"for pyproject.toml version {version!r}.\n"
            "After editing [Unreleased], run: python scripts/bump_release.py <new_version>",
            file=sys.stderr,
        )
        return 1
    print(f"ok: CHANGELOG.md documents release {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
