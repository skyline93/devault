from __future__ import annotations

import runpy
from pathlib import Path


def test_verify_compatibility_matrix_script() -> None:
    root = Path(__file__).resolve().parents[1]
    ns = runpy.run_path(str(root / "scripts" / "verify_compatibility_matrix.py"))
    assert ns["verify"]() == 0
