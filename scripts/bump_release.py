#!/usr/bin/env python3
"""
Bump ``[project].version`` in pyproject.toml, fold ``[Unreleased]`` into ``[new_version]``,
and set ``docs/compatibility.json`` → ``current.control_plane_release`` to the same version.

Prerequisites:
  - ``CHANGELOG.md`` has a ``## [Unreleased]`` block followed by ``---`` then ``## [previous]``.
  - The Unreleased body contains at least one bullet line (``- ...``).

Usage:
  python scripts/bump_release.py 0.5.0
  python scripts/bump_release.py 0.5.0 --dry-run
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import tomllib
from pathlib import Path


_UNRELEASED_TEMPLATE = """## [Unreleased]

### Added

### Changed

### Deprecated

### Removed

### Fixed

### Security

"""

_UNRELEASED_FOLD_RE = re.compile(
    r"^(## \[Unreleased\]\s*\n)(.*?)(\n---\s*\n+)(## \[)",
    re.MULTILINE | re.DOTALL,
)

_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def _project_version(pyproject_path: Path) -> str:
    return str(tomllib.loads(pyproject_path.read_text(encoding="utf-8"))["project"]["version"])


def _set_project_version(pyproject_path: Path, new_version: str) -> str:
    text = pyproject_path.read_text(encoding="utf-8")
    old = _project_version(pyproject_path)
    token = f'version = "{old}"'
    if text.count(token) != 1:
        raise SystemExit(f"error: expected exactly one {token!r} in pyproject.toml")
    return text.replace(token, f'version = "{new_version}"', 1)


def sync_compatibility_current_release(repo: Path, new_version: str) -> None:
    """Set ``docs/compatibility.json`` → ``current.control_plane_release`` to match the release."""
    path = repo / "docs" / "compatibility.json"
    if not path.is_file():
        raise SystemExit(f"error: missing {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    cur = data.get("current")
    if not isinstance(cur, dict):
        raise SystemExit("error: compatibility.json missing current object")
    cur["control_plane_release"] = new_version
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _fold_changelog(changelog_text: str, new_version: str, release_date: str) -> str:
    m = _UNRELEASED_FOLD_RE.search(changelog_text)
    if not m:
        raise SystemExit(
            "error: CHANGELOG.md must contain ## [Unreleased] ... --- ... ## [ ... for folding"
        )
    body = m.group(2).rstrip()
    if not re.search(r"^\s*-\s", body, re.MULTILINE):
        raise SystemExit(
            "error: [Unreleased] has no bullet entries (- ...); nothing to fold for a release"
        )
    folded = (
        f"{_UNRELEASED_TEMPLATE.rstrip()}\n\n---\n\n"
        f"## [{new_version}] - {release_date}\n\n"
        f"{body}\n\n---\n\n"
        f"## ["
    )
    return changelog_text[: m.start()] + folded + changelog_text[m.end() :]


def main() -> int:
    parser = argparse.ArgumentParser(description="Bump version and fold CHANGELOG [Unreleased].")
    parser.add_argument("new_version", help="SemVer release, e.g. 0.5.0")
    parser.add_argument("--date", help="ISO date for changelog heading (default: today UTC)")
    parser.add_argument("--dry-run", action="store_true", help="Print actions only")
    args = parser.parse_args()
    new_v = args.new_version.strip()
    if not _SEMVER_RE.match(new_v):
        print("error: new_version must look like MAJOR.MINOR.PATCH", file=sys.stderr)
        return 1

    repo = Path(__file__).resolve().parents[1]
    pyproject_path = repo / "pyproject.toml"
    changelog_path = repo / "CHANGELOG.md"
    old_v = _project_version(pyproject_path)
    if new_v == old_v:
        print(f"error: pyproject.toml is already {new_v!r}", file=sys.stderr)
        return 1

    release_date = args.date or dt.date.today().isoformat()
    new_pyproject = _set_project_version(pyproject_path, new_v)
    new_changelog = _fold_changelog(changelog_path.read_text(encoding="utf-8"), new_v, release_date)

    if args.dry_run:
        print(f"Would set pyproject.toml: {old_v!r} -> {new_v!r}")
        print(f"Would fold CHANGELOG [Unreleased] into [{new_v}] - {release_date}")
        print(f"Would set docs/compatibility.json current.control_plane_release -> {new_v!r}")
        return 0

    pyproject_path.write_text(new_pyproject, encoding="utf-8")
    changelog_path.write_text(new_changelog, encoding="utf-8")
    sync_compatibility_current_release(repo, new_v)
    print(f"Updated pyproject.toml: {old_v!r} -> {new_v!r}")
    print(f"Folded CHANGELOG [Unreleased] into [{new_v}] - {release_date}")
    print(f"Updated docs/compatibility.json current.control_plane_release -> {new_v!r}")
    print("Next: review diff, commit, tag, publish.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
