from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def _load_ci_e2e_matrix_plan():
    path = REPO / "scripts" / "ci_e2e_matrix_plan.py"
    spec = importlib.util.spec_from_file_location("_ci_e2e_matrix_plan", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_build_rows_homogeneous_only_when_prev_empty() -> None:
    build_rows = _load_ci_e2e_matrix_plan().build_rows

    rows = build_rows("abc123", "")
    assert rows == [{"id": "homogeneous", "cp_ref": "abc123", "agent_ref": "abc123"}]


def test_build_rows_includes_cross_when_prev_set() -> None:
    build_rows = _load_ci_e2e_matrix_plan().build_rows

    rows = build_rows("abc123", "v0.3.0")
    assert len(rows) == 3
    assert rows[0]["id"] == "homogeneous"
    assert rows[1] == {"id": "cp_current_agent_prev_minor", "cp_ref": "abc123", "agent_ref": "v0.3.0"}
    assert rows[2] == {"id": "cp_prev_minor_agent_current", "cp_ref": "v0.3.0", "agent_ref": "abc123"}


def test_ci_e2e_matrix_plan_emits_json_to_stdout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    monkeypatch.setenv("GITHUB_SHA", "deadbeef")
    proc = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "ci_e2e_matrix_plan.py")],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(proc.stdout.strip())
    assert "include" in data
    assert len(data["include"]) >= 1


def test_build_rows_requires_sha() -> None:
    build_rows = _load_ci_e2e_matrix_plan().build_rows

    with pytest.raises(ValueError):
        build_rows("", "")
