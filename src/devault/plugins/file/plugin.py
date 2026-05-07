from __future__ import annotations

import hashlib
import json
import os
import tarfile
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pathspec
from sqlalchemy.orm import Session

from devault.db.models import Artifact, Job
from devault.settings import Settings
from devault.storage.types import Storage


class FileBackupError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _validate_paths(paths: list[str], allowed_prefixes: list[str] | None) -> list[Path]:
    if not paths:
        raise FileBackupError("INVALID_CONFIG", "paths must be a non-empty list")
    resolved: list[Path] = []
    for raw in paths:
        p = Path(raw)
        if not p.is_absolute():
            raise FileBackupError("INVALID_CONFIG", f"Path must be absolute: {raw!r}")
        try:
            rp = p.resolve(strict=False)
        except OSError as e:
            raise FileBackupError("PATH_NOT_FOUND", f"Cannot resolve {raw!r}: {e}") from e
        if allowed_prefixes:
            ok = any(str(rp).startswith(prefix) for prefix in allowed_prefixes)
            if not ok:
                raise FileBackupError(
                    "PATH_NOT_ALLOWED",
                    f"Path {rp} is not under allowed prefixes: {allowed_prefixes}",
                )
        if not rp.exists():
            raise FileBackupError("PATH_NOT_FOUND", f"Path does not exist: {rp}")
        resolved.append(rp)
    return resolved


def _pathspec_from_excludes(excludes: list[str] | None) -> pathspec.PathSpec | None:
    if not excludes:
        return None
    return pathspec.PathSpec.from_lines("gitwildmatch", excludes)


def _iter_file_entries(
    roots: list[Path],
    excludes: pathspec.PathSpec | None,
) -> list[tuple[Path, str]]:
    entries: list[tuple[Path, str]] = []
    for idx, root in enumerate(roots):
        if root.is_symlink():
            raise FileBackupError("SYMLINK_ROOT", f"Symlink root not supported: {root}")
        if root.is_file():
            arcname = f"sources/{idx}/{root.name}"
            if excludes and excludes.match_file(arcname):
                continue
            entries.append((root, arcname))
            continue
        if not root.is_dir():
            raise FileBackupError("INVALID_PATH", f"Not a file or directory: {root}")
        for dirpath, _dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
            for name in filenames:
                full = Path(dirpath) / name
                try:
                    rel_within = full.relative_to(root)
                except ValueError:
                    continue
                arcname = f"sources/{idx}/{rel_within.as_posix()}"
                if excludes and excludes.match_file(arcname):
                    continue
                if full.is_symlink():
                    continue
                if not full.is_file():
                    continue
                entries.append((full, arcname))
    return entries


def _sha256_file(path: Path, chunk: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _artifact_prefix(settings: Settings, job_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)
    return f"devault/{settings.env_name}/artifacts/{now:%Y/%m/%d}/{job_id}"


@dataclass
class BackupOutcome:
    bundle_key: str
    manifest_key: str
    size_bytes: int
    checksum_sha256: str
    manifest: dict


def run_file_backup(
    *,
    job: Job,
    settings: Settings,
    storage: Storage,
) -> BackupOutcome:
    cfg = job.config_snapshot or {}
    if cfg.get("version") != 1:
        raise FileBackupError("INVALID_CONFIG", "config.version must be 1")
    paths = cfg.get("paths") or []
    excludes = cfg.get("excludes") or []
    roots = _validate_paths(paths, settings.allowed_prefix_list)
    spec = _pathspec_from_excludes(excludes)
    file_entries = _iter_file_entries(roots, spec)
    if not file_entries:
        raise FileBackupError("EMPTY_BACKUP", "No files matched the given paths and excludes")

    prefix = _artifact_prefix(settings, job.id)
    bundle_key = f"{prefix}/bundle.tar.gz"
    manifest_key = f"{prefix}/manifest.json"

    files_meta: list[dict] = []
    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        with tarfile.open(tmp_path, "w:gz", format=tarfile.PAX_FORMAT) as tf:
            for full, arcname in file_entries:
                st = full.stat()
                files_meta.append(
                    {
                        "path": arcname,
                        "size": st.st_size,
                        "mtime": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
                        "mode": st.st_mode,
                    }
                )
                # Avoid passing `filter=` to `TarFile.add`: signature differs across Python versions.
                tf.add(str(full), arcname=arcname, recursive=False)

        size_bytes = tmp_path.stat().st_size
        checksum = _sha256_file(tmp_path)

        manifest = {
            "schema_version": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "plugin": "file",
            "paths": paths,
            "excludes": excludes,
            "archive_format": "tar.gz",
            "files": files_meta,
            "bundle_object_key": bundle_key,
            "checksum_sha256": checksum,
            "size_bytes": size_bytes,
        }
        manifest_bytes = json.dumps(manifest, indent=2).encode("utf-8")

        storage.put_file(bundle_key, tmp_path)
        storage.put_bytes(manifest_key, manifest_bytes)

        if storage.backend_name == "local":
            if not storage.exists(bundle_key) or not storage.exists(manifest_key):
                raise FileBackupError("STORAGE_ERROR", "Uploaded objects not found")
        return BackupOutcome(
            bundle_key=bundle_key,
            manifest_key=manifest_key,
            size_bytes=size_bytes,
            checksum_sha256=checksum,
            manifest=manifest,
        )
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass


def run_file_restore(
    *,
    db: Session,
    job: Job,
    settings: Settings,
    storage: Storage,
) -> None:
    cfg = job.config_snapshot or {}
    artifact_id = cfg.get("artifact_id") or str(job.restore_artifact_id or "")
    if not artifact_id:
        raise FileBackupError("INVALID_CONFIG", "artifact_id required for restore")
    try:
        aid = uuid.UUID(str(artifact_id))
    except ValueError as e:
        raise FileBackupError("INVALID_CONFIG", "artifact_id must be a UUID") from e

    target_raw = cfg.get("target_path")
    if not target_raw or not isinstance(target_raw, str):
        raise FileBackupError("INVALID_CONFIG", "target_path required")
    target = Path(target_raw)
    if not target.is_absolute():
        raise FileBackupError("INVALID_CONFIG", "target_path must be absolute")
    target = target.resolve(strict=False)
    if settings.allowed_prefix_list:
        ok = any(str(target).startswith(prefix) for prefix in settings.allowed_prefix_list)
        if not ok:
            raise FileBackupError(
                "PATH_NOT_ALLOWED",
                f"target_path {target} not under allowed prefixes",
            )

    confirm = bool(cfg.get("confirm_overwrite_non_empty"))
    if target.exists() and any(target.iterdir()) and not confirm:
        raise FileBackupError(
            "TARGET_NOT_EMPTY",
            "target_path exists and is not empty; pass confirm_overwrite_non_empty=true",
        )

    art = db.get(Artifact, aid)
    if art is None:
        raise FileBackupError("ARTIFACT_NOT_FOUND", f"No artifact {aid}")

    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
        bundle_local = Path(tmp.name)
    try:
        storage.get_file(art.bundle_key, bundle_local)
        digest = _sha256_file(bundle_local)
        if digest.lower() != art.checksum_sha256.lower():
            raise FileBackupError("CHECKSUM_MISMATCH", "Downloaded bundle checksum mismatch")

        target.mkdir(parents=True, exist_ok=True)
        with tarfile.open(bundle_local, "r:gz") as tf:
            # Safe extraction when supported (3.11+ / 3.12+ varies); fall back otherwise.
            try:
                tf.extractall(path=target, filter="data")  # type: ignore[call-arg]
            except TypeError:
                tf.extractall(path=target)
    finally:
        try:
            bundle_local.unlink(missing_ok=True)
        except OSError:
            pass
