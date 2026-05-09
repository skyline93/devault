"""DeVault — backup platform (file plugin MVP)."""

from __future__ import annotations

import importlib.metadata
from pathlib import Path


def _version_from_pyproject(repo_root: Path) -> str:
    import tomllib

    data = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def _read_version() -> str:
    """Release version: editable/metadata when installed, else repo ``pyproject.toml``."""
    try:
        return importlib.metadata.version("devault")
    except importlib.metadata.PackageNotFoundError:
        pass
    # e.g. pytest with ``pythonpath = ["src"]`` and no ``pip install -e .``
    here = Path(__file__).resolve()
    repo_root = here.parents[2]
    pyproject = repo_root / "pyproject.toml"
    if pyproject.is_file():
        return _version_from_pyproject(repo_root)
    return "0.0.0"


__version__ = _read_version()
