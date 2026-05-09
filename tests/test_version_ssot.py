"""Release version matches ``pyproject.toml`` (SSOT)."""

from __future__ import annotations

import tomllib
from pathlib import Path

import devault


def test_version_matches_pyproject() -> None:
    repo = Path(__file__).resolve().parents[1]
    expected = str(
        tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    )
    assert devault.__version__ == expected
