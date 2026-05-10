"""path_precheck shared path existence/readability logic."""

from __future__ import annotations

from pathlib import Path

from devault.services.path_precheck import path_precheck_report


def test_path_precheck_report_ok(tmp_path: Path) -> None:
    f = tmp_path / "a.txt"
    f.write_text("x", encoding="utf-8")
    ok, rep = path_precheck_report([str(f)])
    assert ok is True
    assert rep["schema"] == "devault-path-precheck-report-v1"
    assert rep["paths"][0]["exists"] is True
    assert rep["paths"][0]["readable"] is True


def test_path_precheck_report_missing() -> None:
    ok, rep = path_precheck_report(["/nonexistent/path/devault-precheck-xyz"])
    assert ok is False
    assert rep["paths"][0]["exists"] is False
    assert rep["paths"][0]["readable"] is False
