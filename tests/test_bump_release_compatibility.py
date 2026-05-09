from __future__ import annotations

import json
import runpy
from pathlib import Path


def test_sync_compatibility_current_release_updates_json(tmp_path: Path) -> None:
    repo = tmp_path
    doc = repo / "docs"
    doc.mkdir()
    path = doc / "compatibility.json"
    path.write_text(
        json.dumps({"schema_version": 1, "current": {"control_plane_release": "0.1.0", "x": 1}}),
        encoding="utf-8",
    )
    root = Path(__file__).resolve().parents[1]
    ns = runpy.run_path(str(root / "scripts" / "bump_release.py"))
    ns["sync_compatibility_current_release"](repo, "0.9.0")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["current"]["control_plane_release"] == "0.9.0"
    assert data["current"]["x"] == 1
