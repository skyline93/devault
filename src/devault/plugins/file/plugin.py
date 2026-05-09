from __future__ import annotations

import hashlib
import json
import os
import tarfile
import tempfile
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pathspec
from sqlalchemy.orm import Session

from devault import __version__
from devault.db.models import Artifact, Job
from devault.grpc_gen import agent_pb2
from devault.release_meta import GRPC_API_PACKAGE
from devault.settings import Settings
from devault.storage.multipart import part_count
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


def artifact_object_keys(settings: Settings, job_id: uuid.UUID) -> tuple[str, str]:
    """Stable S3 keys for a job artifact (control plane and agent must agree)."""
    prefix = f"devault/{settings.env_name}/artifacts/{job_id}"
    return f"{prefix}/bundle.tar.gz", f"{prefix}/manifest.json"


@dataclass
class BackupOutcome:
    bundle_key: str
    manifest_key: str
    size_bytes: int
    checksum_sha256: str
    manifest: dict


def _build_backup_tarball(
    job: Job,
    settings: Settings,
    *,
    bundle_key: str,
    manifest_key: str,
) -> tuple[Path, dict, int, str]:
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
                tf.add(str(full), arcname=arcname, recursive=False)

        size_bytes = tmp_path.stat().st_size
        checksum = _sha256_file(tmp_path)

        manifest = {
            "schema_version": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "devault_release": __version__,
            "grpc_proto_package": GRPC_API_PACKAGE,
            "plugin": "file",
            "paths": paths,
            "excludes": excludes,
            "archive_format": "tar.gz",
            "files": files_meta,
            "bundle_object_key": bundle_key,
            "checksum_sha256": checksum,
            "size_bytes": size_bytes,
        }
        return tmp_path, manifest, size_bytes, checksum
    except Exception:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def run_file_backup(
    *,
    job: Job,
    settings: Settings,
    storage: Storage,
) -> BackupOutcome:
    bundle_key, manifest_key = artifact_object_keys(settings, job.id)
    tmp_path, manifest, size_bytes, checksum = _build_backup_tarball(
        job,
        settings,
        bundle_key=bundle_key,
        manifest_key=manifest_key,
    )
    try:
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


def http_put_presigned_file(url: str, path: Path, *, timeout: float = 7200.0) -> None:
    """Stream from disk to avoid loading the whole bundle into memory."""
    with path.open("rb") as body, httpx.Client(timeout=timeout) as client:
        r = client.put(url, content=body)
        r.raise_for_status()


def http_put_presigned_bytes(url: str, data: bytes, *, timeout: float = 600.0) -> None:
    with httpx.Client(timeout=timeout) as client:
        r = client.put(url, content=data)
        r.raise_for_status()


def _http_put_presigned_chunk_with_retries(
    url: str,
    data: bytes,
    *,
    timeout: float = 7200.0,
    attempts: int = 6,
) -> str:
    delay = 1.0
    last_err: BaseException | None = None
    for _ in range(attempts):
        try:
            with httpx.Client(timeout=timeout) as client:
                r = client.put(url, content=data)
                r.raise_for_status()
            etag = (r.headers.get("etag") or "").strip()
            if not etag:
                raise FileBackupError("UPLOAD", "S3 part upload response missing ETag")
            return etag
        except (httpx.HTTPError, OSError, FileBackupError) as e:
            last_err = e
            time.sleep(delay)
            delay = min(delay * 2.0, 30.0)
    raise FileBackupError("UPLOAD", f"S3 multipart part upload failed: {last_err!r}") from last_err


def http_download_file_streaming_sha256(url: str, dest: Path, *, timeout: float = 7200.0) -> str:
    """Download to ``dest`` and return SHA-256 hex of bytes written (streaming)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha256()
    with dest.open("wb") as out, httpx.Client(timeout=timeout, follow_redirects=True) as client:
        with client.stream("GET", url) as r:
            r.raise_for_status()
            for chunk in r.iter_bytes(1024 * 1024):
                out.write(chunk)
                h.update(chunk)
    return h.hexdigest()


def write_multipart_checkpoint(
    path: Path,
    *,
    upload_id: str,
    bundle_key: str,
    manifest_key: str,
    content_length: int,
    part_size: int,
    checksum_sha256: str,
    manifest: dict,
    parts: list[dict],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "upload_id": upload_id,
                "bundle_key": bundle_key,
                "manifest_key": manifest_key,
                "content_length": content_length,
                "part_size": part_size,
                "checksum_sha256": checksum_sha256,
                "manifest": manifest,
                "parts": parts,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def upload_backup_via_storage_grant(
    tmp_path: Path,
    manifest_bytes: bytes,
    grant: agent_pb2.RequestStorageGrantReply,
    *,
    timeout: float = 7200.0,
    multipart_checkpoint_path: Path | None = None,
    multipart_checkpoint_fields: dict | None = None,
) -> str | None:
    """Upload manifest and bundle (single PUT or multipart). Returns JSON for CompleteJob multipart fields or None.

    ``multipart_checkpoint_fields`` must include ``manifest`` (dict), ``content_length`` (int),
    ``checksum_sha256`` (str) when ``multipart_checkpoint_path`` is set for resume support.
    """
    http_put_presigned_bytes(grant.manifest_http_url, manifest_bytes, timeout=timeout)
    if grant.bundle_multipart_upload_id:
        ps = int(grant.bundle_multipart_part_size_bytes or 0)
        uid = (grant.bundle_multipart_upload_id or "").strip()
        completed = (grant.bundle_multipart_completed_parts_json or "").strip()
        if completed:
            try:
                meta_raw = json.loads(completed)
            except json.JSONDecodeError as e:
                raise FileBackupError("INVALID_GRANT", "invalid bundle_multipart_completed_parts_json") from e
            if not isinstance(meta_raw, list) or not meta_raw:
                raise FileBackupError("INVALID_GRANT", "bundle_multipart_completed_parts_json must be a list")
            meta = [{"PartNumber": int(p["PartNumber"]), "ETag": str(p["ETag"])} for p in meta_raw]
            if multipart_checkpoint_path and multipart_checkpoint_fields:
                mf = multipart_checkpoint_fields
                write_multipart_checkpoint(
                    multipart_checkpoint_path,
                    upload_id=uid,
                    bundle_key=grant.bundle_key,
                    manifest_key=grant.manifest_key,
                    content_length=int(mf["content_length"]),
                    part_size=ps,
                    checksum_sha256=str(mf["checksum_sha256"]),
                    manifest=dict(mf["manifest"]),
                    parts=meta,
                )
            return json.dumps(meta)

        parts_sorted = sorted(grant.bundle_multipart_parts, key=lambda p: p.part_number)
        if not parts_sorted or ps <= 0:
            raise FileBackupError("INVALID_GRANT", "invalid multipart grant")
        meta: list[dict] = []
        if multipart_checkpoint_path and multipart_checkpoint_path.exists():
            try:
                ck = json.loads(multipart_checkpoint_path.read_text(encoding="utf-8"))
                if ck.get("upload_id") == uid:
                    prev = ck.get("parts") or []
                    if isinstance(prev, list):
                        meta = [
                            {"PartNumber": int(p["PartNumber"]), "ETag": str(p["ETag"])}
                            for p in prev
                            if isinstance(p, dict) and "PartNumber" in p and "ETag" in p
                        ]
            except (OSError, json.JSONDecodeError, TypeError, ValueError, KeyError):
                meta = []
        done = {int(p["PartNumber"]) for p in meta}
        mf = multipart_checkpoint_fields or {}
        manifest_d = dict(mf["manifest"]) if isinstance(mf.get("manifest"), dict) else {}
        flen = tmp_path.stat().st_size
        total_parts = part_count(flen, ps)
        with tmp_path.open("rb") as f:
            for part in parts_sorted:
                pn = int(part.part_number)
                if pn in done:
                    continue
                offset = (pn - 1) * ps
                f.seek(offset)
                if pn < total_parts:
                    chunk = f.read(ps)
                else:
                    chunk = f.read()
                if not chunk:
                    raise FileBackupError("UPLOAD", f"empty chunk for multipart part {pn}")
                etag = _http_put_presigned_chunk_with_retries(
                    part.http_put_url,
                    chunk,
                    timeout=timeout,
                )
                meta.append({"PartNumber": pn, "ETag": etag})
                meta.sort(key=lambda x: int(x["PartNumber"]))
                if multipart_checkpoint_path and multipart_checkpoint_fields:
                    write_multipart_checkpoint(
                        multipart_checkpoint_path,
                        upload_id=uid,
                        bundle_key=grant.bundle_key,
                        manifest_key=grant.manifest_key,
                        content_length=int(multipart_checkpoint_fields["content_length"]),
                        part_size=ps,
                        checksum_sha256=str(multipart_checkpoint_fields["checksum_sha256"]),
                        manifest=manifest_d,
                        parts=meta,
                    )
        meta.sort(key=lambda x: int(x["PartNumber"]))
        return json.dumps(meta)
    if not grant.bundle_http_url:
        raise FileBackupError("INVALID_GRANT", "missing bundle_http_url")
    http_put_presigned_file(grant.bundle_http_url, tmp_path, timeout=timeout)
    return None


def run_file_backup_with_presigned_urls(
    *,
    job: Job,
    settings: Settings,
    bundle_put_url: str,
    manifest_put_url: str,
) -> BackupOutcome:
    bundle_key, manifest_key = artifact_object_keys(settings, job.id)
    tmp_path, manifest, size_bytes, checksum = _build_backup_tarball(
        job,
        settings,
        bundle_key=bundle_key,
        manifest_key=manifest_key,
    )
    try:
        manifest_bytes = json.dumps(manifest, indent=2).encode("utf-8")
        http_put_presigned_file(bundle_put_url, tmp_path)
        http_put_presigned_bytes(manifest_put_url, manifest_bytes)
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


def _restore_paths_and_target(job: Job, settings: Settings) -> tuple[uuid.UUID, Path, bool]:
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
    return aid, target, confirm


def run_file_restore(
    *,
    db: Session,
    job: Job,
    settings: Settings,
    storage: Storage,
) -> None:
    aid, target, _confirm = _restore_paths_and_target(job, settings)

    art = db.get(Artifact, aid)
    if art is None:
        raise FileBackupError("ARTIFACT_NOT_FOUND", f"No artifact {aid}")

    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
        bundle_local = Path(tmp.name)
    try:
        storage.get_file(art.bundle_key, bundle_local)
        _extract_bundle(bundle_local, target, art.checksum_sha256)
    finally:
        try:
            bundle_local.unlink(missing_ok=True)
        except OSError:
            pass


def _extract_bundle(bundle_local: Path, target: Path, expected_checksum: str) -> None:
    digest = _sha256_file(bundle_local)
    if digest.lower() != expected_checksum.lower():
        raise FileBackupError("CHECKSUM_MISMATCH", "Downloaded bundle checksum mismatch")

    target.mkdir(parents=True, exist_ok=True)
    with tarfile.open(bundle_local, "r:gz") as tf:
        try:
            tf.extractall(path=target, filter="data")  # type: ignore[call-arg]
        except TypeError:
            tf.extractall(path=target)


def run_file_restore_with_presigned_bundle(
    *,
    job: Job,
    settings: Settings,
    bundle_get_url: str,
    expected_checksum_sha256: str,
) -> None:
    _, target, _confirm = _restore_paths_and_target(job, settings)

    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
        bundle_local = Path(tmp.name)
    try:
        digest = http_download_file_streaming_sha256(bundle_get_url, bundle_local)
        if digest.lower() != expected_checksum_sha256.lower():
            raise FileBackupError("CHECKSUM_MISMATCH", "Downloaded bundle checksum mismatch")
        _extract_bundle(bundle_local, target, digest)
    finally:
        try:
            bundle_local.unlink(missing_ok=True)
        except OSError:
            pass
