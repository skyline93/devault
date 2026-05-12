from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Long-running backups may exceed default; override via env in production.
_DEFAULT_TIMEOUT_SEC = int(os.environ.get("DEVAULT_PGBACKREST_JOB_TIMEOUT_SEC", "7200"))


def _s3_repo1_path_from_prefix(prefix: str) -> str:
    """Map API/repo_s3_prefix to pgBackRest repo1-path (path inside the bucket)."""
    p = (prefix or "").strip().replace("\\", "/").strip("/")
    if not p:
        return "/"
    return "/" + p


def _write_pgbackrest_conf(cfg: dict[str, Any], *, path: Path) -> None:
    """Write a minimal pgBackRest config file from non-secret job snapshot fields."""
    stanza = str(cfg.get("stanza") or "").strip()
    pg_host = str(cfg.get("pg_host") or "").strip()
    pg_port = int(cfg.get("pg_port") or 5432)
    pg_data_path = str(cfg.get("pg_data_path") or "").strip()
    log_dir = path.parent / "pgbr-logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "[global]",
        f"log-path={log_dir}",
    ]
    bucket = (cfg.get("repo_s3_bucket") or "").strip()
    prefix = (cfg.get("repo_s3_prefix") or "").strip()
    region = (cfg.get("repo_s3_region") or "").strip()
    endpoint = (cfg.get("repo_s3_endpoint") or "").strip()
    repo_path = (cfg.get("repo_path") or "").strip()
    if bucket:
        lines.append("repo1-type=s3")
        lines.append(f"repo1-s3-bucket={bucket}")
        lines.append(f"repo1-path={_s3_repo1_path_from_prefix(prefix)}")
        if region:
            lines.append(f"repo1-s3-region={region}")
        if endpoint:
            lines.append(f"repo1-s3-endpoint={endpoint}")
            if endpoint.lower().startswith("http://"):
                lines.append("repo1-storage-verify-tls=n")
    elif repo_path:
        lines.append(f"repo1-path={repo_path}")
    else:
        raise ValueError("repo_s3_bucket+repo_s3_prefix or repo_path required")
    lines.append("")
    lines.append(f"[{stanza}]")
    lines.append(f"pg1-host={pg_host}")
    lines.append(f"pg1-port={pg_port}")
    lines.append(f"pg1-path={pg_data_path}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_pgbackrest_job(cfg: dict[str, Any], *, timeout_sec: int | None = None) -> dict[str, Any]:
    """Run pgbackrest backup or expire; return a dict suitable for CompleteJob.result_summary_json."""
    op = str(cfg.get("pgbackrest_operation") or "backup").strip().lower()
    timeout = timeout_sec if timeout_sec is not None else _DEFAULT_TIMEOUT_SEC
    exe = os.environ.get("DEVAULT_PGBACKREST_BIN", "pgbackrest")
    stanza = str(cfg.get("stanza") or "").strip()
    if not stanza:
        raise ValueError("stanza is required")

    with tempfile.TemporaryDirectory(prefix="devault-pgbr-") as tmp:
        tmp_path = Path(tmp)
        conf = tmp_path / "pgbackrest.conf"
        _write_pgbackrest_conf(cfg, path=conf)
        env = os.environ.copy()
        if op == "expire":
            argv = [exe, f"--config={conf}", f"--stanza={stanza}", "expire"]
        else:
            btype = str(cfg.get("backup_type") or "").strip().lower()
            if btype not in ("full", "incr"):
                raise ValueError("backup_type must be full or incr for backup operation")
            argv = [exe, f"--config={conf}", f"--stanza={stanza}", "--type=" + btype, "backup"]

        logger.info("running pgbackrest argv=%s", argv)
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False,
        )
        out: dict[str, Any] = {
            "pgbackrest_operation": op,
            "stanza": stanza,
            "exit_code": proc.returncode,
            "stdout_tail": (proc.stdout or "")[-8000:],
            "stderr_tail": (proc.stderr or "")[-8000:],
        }
        if proc.returncode != 0:
            return out

        info_argv = [exe, f"--config={conf}", f"--stanza={stanza}", "info", "--output=json"]
        try:
            info_proc = subprocess.run(
                info_argv,
                capture_output=True,
                text=True,
                timeout=min(120, timeout),
                env=env,
                check=False,
            )
            if info_proc.returncode == 0 and (info_proc.stdout or "").strip():
                try:
                    out["pgbackrest_info"] = json.loads(info_proc.stdout)
                except json.JSONDecodeError:
                    out["pgbackrest_info_raw"] = (info_proc.stdout or "")[:32000]
            else:
                out["pgbackrest_info_error"] = (info_proc.stderr or "")[:2000]
        except subprocess.TimeoutExpired:
            out["pgbackrest_info_error"] = "timeout"
        return out
