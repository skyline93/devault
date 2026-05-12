from __future__ import annotations

import json
import logging
import os
import platform
import socket
import shutil
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace

import grpc  # pyright: ignore[reportMissingModuleSource]

from devault import __version__
from devault.agent.capabilities import gate_multipart_resume, gate_multipart_upload
from devault.core.enums import JobKind, PluginName
from devault.grpc_gen import agent_pb2, agent_pb2_grpc
from devault.plugins.file import FileBackupError, run_file_restore_with_presigned_bundle
from devault.plugins.file.multipart_wip import (
    bundle_wip_path,
    checkpoint_path,
    clear_job_multipart_state,
)
from devault.plugins.file.multipart_resume import validate_multipart_resume_checkpoint
from devault.plugins.file.plugin import (
    BackupOutcome,
    _build_backup_tarball,
    artifact_object_keys,
    finalize_bundle_with_optional_encryption,
    upload_backup_via_storage_grant,
    write_multipart_checkpoint,
)
from devault.services.path_precheck import path_precheck_report
from devault.settings import Settings, get_settings

logger = logging.getLogger(__name__)

@dataclass
class AgentCapabilityState:
    """Latest ``server_capabilities`` from Register / Heartbeat (empty set if none advertised yet)."""

    caps: frozenset[str] = field(default_factory=frozenset)


_FATAL_VERSION_REASONS = frozenset(
    {
        "AGENT_VERSION_TOO_OLD",
        "AGENT_PROTO_PACKAGE_MISMATCH",
        "AGENT_VERSION_REQUIRED",
        "AGENT_VERSION_UNPARSEABLE",
    }
)


def _trailing_reason_code(exc: grpc.RpcError) -> str | None:
    try:
        md = exc.trailing_metadata()
    except Exception:
        return None
    if not md:
        return None
    for k, v in md:
        if k == "devault-reason-code":
            if isinstance(v, bytes):
                return v.decode("ascii", errors="replace")
            return str(v)
    return None


def _agent_identity_fields(settings: Settings) -> tuple[str, str, str]:
    return __version__, agent_pb2.DESCRIPTOR.package, (settings.agent_git_commit or "").strip()


def _build_channel(target: str, *, settings: Settings) -> grpc.Channel:
    opts: list[tuple[str, str]] = []
    if settings.grpc_tls_server_name:
        opts.append(("grpc.ssl_target_name_override", settings.grpc_tls_server_name))
    if settings.grpc_tls_ca_path:
        ca = Path(settings.grpc_tls_ca_path).read_bytes()
        client_key: bytes | None = None
        client_chain: bytes | None = None
        if settings.grpc_tls_client_cert_path and settings.grpc_tls_client_key_path:
            client_chain = Path(settings.grpc_tls_client_cert_path).read_bytes()
            client_key = Path(settings.grpc_tls_client_key_path).read_bytes()
        creds = grpc.ssl_channel_credentials(
            root_certificates=ca,
            private_key=client_key,
            certificate_chain=client_chain,
        )
        return grpc.secure_channel(target, creds, options=opts or None)
    return grpc.insecure_channel(target, options=opts or None)


def _metadata(token: str | None) -> list[tuple[str, str]]:
    if not token:
        return []
    return [("authorization", f"Bearer {token}")]


def _job_view(job_id: str, lease: agent_pb2.JobLease, cfg: dict) -> SimpleNamespace:
    rid = cfg.get("artifact_id")
    restore_aid = uuid.UUID(str(rid)) if rid else None
    return SimpleNamespace(
        id=uuid.UUID(job_id),
        kind=lease.kind,
        plugin=lease.plugin,
        status="running",
        trigger="manual",
        config_snapshot=cfg,
        restore_artifact_id=restore_aid,
    )


def _agent_state_path(settings: Settings) -> Path:
    return settings.agent_multipart_state_root / "agent_instance.json"


def _load_persisted_agent_id(settings: Settings) -> str | None:
    path = _agent_state_path(settings)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        raw = str(data.get("agent_id") or "").strip()
        return raw or None
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None


def _persist_agent_id(settings: Settings, agent_id: str) -> None:
    path = _agent_state_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"agent_id": agent_id}), encoding="utf-8")


def _register_agent(
    stub: agent_pb2_grpc.AgentControlStub,
    *,
    bearer: str,
    agent_id: str | None,
    settings: Settings,
    cap_state: AgentCapabilityState,
) -> str:
    rel, pkg, gc = _agent_identity_fields(settings)
    prefixes = settings.allowed_prefix_list or []
    region = (os.environ.get("DEVAULT_AGENT_REGION") or "").strip()
    env_tag = (os.environ.get("DEVAULT_AGENT_ENV") or settings.env_name or "").strip()
    reply = stub.Register(
        agent_pb2.RegisterRequest(
            agent_id=agent_id or "",
            agent_release=rel,
            proto_package=pkg,
            git_commit=gc,
            hostname=socket.gethostname(),
            os=f"{platform.system()} {platform.release()}".strip(),
            region=region,
            env=env_tag,
            backup_path_allowlist=prefixes,
            snapshot_schema_version=1,
        ),
        metadata=_metadata(bearer),
    )
    if not reply.ok or not (reply.agent_id or "").strip():
        logger.error("Register failed: %s", reply.message or "unknown")
        raise SystemExit(2)
    assigned = reply.agent_id.strip()
    _persist_agent_id(settings, assigned)
    if reply.server_release:
        logger.info("registered agent %s; control plane %s", assigned, reply.server_release)
    else:
        logger.info("registered agent %s", assigned)
    if reply.deprecation_message:
        logger.warning("Register: %s", reply.deprecation_message)
    cap_state.caps = frozenset(reply.server_capabilities)
    return assigned


def _run_one_job(
    stub: agent_pb2_grpc.AgentControlStub,
    agent_id: str,
    lease: agent_pb2.JobLease,
    bearer: str,
    *,
    server_capabilities: frozenset[str],
) -> None:
    s = get_settings()
    job_id = lease.job_id
    md = _metadata(bearer)
    cfg = json.loads(lease.config_json)
    host_snapshot = socket.gethostname()
    try:
        if lease.kind == JobKind.BACKUP.value and lease.plugin == PluginName.POSTGRES_PGBACKREST.value:
            try:
                from devault.plugins.pgbackrest.runner import run_pgbackrest_job

                summary = run_pgbackrest_job(cfg)
            except (ValueError, OSError) as e:
                logger.warning("pgbackrest job failed job_id=%s %s", job_id, e)
                stub.CompleteJob(
                    agent_pb2.CompleteJobRequest(
                        agent_id=agent_id,
                        job_id=job_id,
                        success=False,
                        error_code="PGBR_CONFIG",
                        error_message=str(e)[:7900],
                        bundle_key="",
                        manifest_key="",
                        size_bytes=0,
                        checksum_sha256="",
                        agent_hostname=host_snapshot,
                    ),
                    metadata=md,
                )
            except subprocess.TimeoutExpired as e:
                logger.warning("pgbackrest timeout job_id=%s", job_id)
                stub.CompleteJob(
                    agent_pb2.CompleteJobRequest(
                        agent_id=agent_id,
                        job_id=job_id,
                        success=False,
                        error_code="PGBR_TIMEOUT",
                        error_message=str(e)[:7900],
                        bundle_key="",
                        manifest_key="",
                        size_bytes=0,
                        checksum_sha256="",
                        agent_hostname=host_snapshot,
                    ),
                    metadata=md,
                )
            else:
                if int(summary.get("exit_code") or 1) != 0:
                    msg = (summary.get("stderr_tail") or summary.get("stdout_tail") or "pgbackrest failed")[:7900]
                    stub.CompleteJob(
                        agent_pb2.CompleteJobRequest(
                            agent_id=agent_id,
                            job_id=job_id,
                            success=False,
                            error_code="PGBR_NONZERO",
                            error_message=msg,
                            bundle_key="",
                            manifest_key="",
                            size_bytes=0,
                            checksum_sha256="",
                            agent_hostname=host_snapshot,
                        ),
                        metadata=md,
                    )
                else:
                    stub.CompleteJob(
                        agent_pb2.CompleteJobRequest(
                            agent_id=agent_id,
                            job_id=job_id,
                            success=True,
                            bundle_key="",
                            manifest_key="",
                            size_bytes=0,
                            checksum_sha256="",
                            result_summary_json=json.dumps(summary),
                            agent_hostname=host_snapshot,
                        ),
                        metadata=md,
                    )
        elif lease.kind == JobKind.BACKUP.value and lease.plugin == PluginName.FILE.value:
            job_stub = _job_view(job_id, lease, cfg)
            bid = uuid.UUID(job_id)
            tid_raw = cfg.get("tenant_id")
            if not tid_raw:
                raise FileBackupError(
                    "INVALID_CONFIG",
                    "tenant_id required in job lease config",
                )
            try:
                tenant_uuid = uuid.UUID(str(tid_raw))
            except (ValueError, TypeError) as e:
                raise FileBackupError(
                    "INVALID_CONFIG",
                    "tenant_id must be a UUID",
                ) from e
            bundle_key, manifest_key = artifact_object_keys(s, bid, tenant_uuid)
            ck_path = checkpoint_path(s, job_id)
            wip_bundle = bundle_wip_path(s, job_id)

            resume_upload_id: str | None = None
            ck_data: dict | None = None
            if ck_path.exists():
                try:
                    ck_data = json.loads(ck_path.read_text(encoding="utf-8"))
                    resume_upload_id = (ck_data.get("upload_id") or "").strip() or None
                except (OSError, json.JSONDecodeError, TypeError):
                    ck_data = None
                    resume_upload_id = None

            use_multipart_resume = False
            if resume_upload_id and wip_bundle.is_file() and ck_data is not None:
                if not gate_multipart_resume(server_capabilities):
                    logger.warning(
                        "multipart resume not advertised by server; clearing local multipart state job_id=%s",
                        job_id,
                    )
                    clear_job_multipart_state(s, job_id)
                    ck_data = None
                    resume_upload_id = None
                else:
                    ok_ck, ck_reason = validate_multipart_resume_checkpoint(
                        wip_bundle=wip_bundle,
                        checkpoint=ck_data,
                        policy_config=cfg,
                    )
                    if ok_ck:
                        use_multipart_resume = True
                    else:
                        logger.warning(
                            "multipart resume checkpoint rejected job_id=%s reason=%s; clearing local state",
                            job_id,
                            ck_reason,
                        )
                        clear_job_multipart_state(s, job_id)
                        ck_data = None
                        resume_upload_id = None

            if use_multipart_resume:
                assert ck_data is not None
                tmp_path = wip_bundle
                manifest = ck_data["manifest"]
                size_bytes = int(ck_data["content_length"])
                checksum = str(ck_data["checksum_sha256"])
            else:
                if ck_path.exists() or wip_bundle.parent.is_dir():
                    clear_job_multipart_state(s, job_id)
                tmp_path, manifest, size_bytes, checksum = _build_backup_tarball(
                    job_stub,
                    s,
                    bundle_key=bundle_key,
                    manifest_key=manifest_key,
                )
                tmp_path, manifest, size_bytes, checksum = finalize_bundle_with_optional_encryption(
                    cfg,
                    s,
                    tmp_path,
                    manifest,
                )
                if size_bytes >= int(s.s3_multipart_threshold_bytes) and gate_multipart_upload(
                    server_capabilities
                ):
                    wip_bundle.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(tmp_path), str(wip_bundle))
                    tmp_path = wip_bundle

            try:
                manifest_bytes = json.dumps(manifest, indent=2).encode("utf-8")
                grant_req = agent_pb2.RequestStorageGrantRequest(
                    agent_id=agent_id,
                    job_id=job_id,
                    intent=agent_pb2.STORAGE_INTENT_WRITE,
                    bundle_content_length=size_bytes,
                )
                if resume_upload_id and wip_bundle.is_file():
                    grant_req.resume_bundle_multipart_upload_id = resume_upload_id
                g = stub.RequestStorageGrant(grant_req, metadata=md)
                if g.bundle_multipart_upload_id and not resume_upload_id:
                    write_multipart_checkpoint(
                        ck_path,
                        upload_id=g.bundle_multipart_upload_id,
                        bundle_key=g.bundle_key,
                        manifest_key=g.manifest_key,
                        content_length=size_bytes,
                        part_size=int(g.bundle_multipart_part_size_bytes or 0),
                        checksum_sha256=checksum,
                        manifest=manifest,
                        parts=[],
                    )
                ck_fields = {
                    "manifest": manifest,
                    "content_length": size_bytes,
                    "checksum_sha256": checksum,
                }
                parts_json = upload_backup_via_storage_grant(
                    tmp_path,
                    manifest_bytes,
                    g,
                    timeout=7200.0,
                    multipart_checkpoint_path=ck_path if g.bundle_multipart_upload_id else None,
                    multipart_checkpoint_fields=ck_fields if g.bundle_multipart_upload_id else None,
                )
                outcome = BackupOutcome(
                    bundle_key=g.bundle_key,
                    manifest_key=g.manifest_key,
                    size_bytes=size_bytes,
                    checksum_sha256=checksum,
                    manifest=manifest,
                )
                stub.ReportProgress(
                    agent_pb2.ReportProgressRequest(
                        agent_id=agent_id,
                        job_id=job_id,
                        percent=95,
                        message="uploaded",
                    ),
                    metadata=md,
                )
                stub.CompleteJob(
                    agent_pb2.CompleteJobRequest(
                        agent_id=agent_id,
                        job_id=job_id,
                        success=True,
                        bundle_key=outcome.bundle_key,
                        manifest_key=outcome.manifest_key,
                        size_bytes=outcome.size_bytes,
                        checksum_sha256=outcome.checksum_sha256,
                        bundle_multipart_upload_id=g.bundle_multipart_upload_id or "",
                        bundle_multipart_parts_json=parts_json or "",
                        agent_hostname=host_snapshot,
                    ),
                    metadata=md,
                )
                if g.bundle_multipart_upload_id:
                    clear_job_multipart_state(s, job_id)
            finally:
                try:
                    if tmp_path != wip_bundle:
                        tmp_path.unlink(missing_ok=True)
                except OSError:
                    pass
        elif lease.kind == JobKind.BACKUP.value:
            raise FileBackupError(
                "UNSUPPORTED_PLUGIN",
                f"unsupported backup plugin: {lease.plugin!r}",
            )
        elif lease.kind in (JobKind.RESTORE.value, JobKind.RESTORE_DRILL.value):
            g = stub.RequestStorageGrant(
                agent_pb2.RequestStorageGrantRequest(
                    agent_id=agent_id,
                    job_id=job_id,
                    intent=agent_pb2.STORAGE_INTENT_READ,
                ),
                metadata=md,
            )
            job_stub = _job_view(job_id, lease, cfg)
            expected = g.expected_checksum_sha256 or cfg.get("expected_checksum_sha256")
            if not expected:
                raise FileBackupError(
                    "INVALID_CONFIG",
                    "restore grant missing expected_checksum_sha256",
                )
            drill_rel = __version__ if lease.kind == JobKind.RESTORE_DRILL.value else None
            rep = run_file_restore_with_presigned_bundle(
                job=job_stub,
                settings=s,
                bundle_get_url=g.bundle_http_url,
                expected_checksum_sha256=expected,
                manifest_get_url=(g.manifest_http_url or "").strip() or None,
                agent_release_for_drill=drill_rel,
            )
            stub.CompleteJob(
                agent_pb2.CompleteJobRequest(
                    agent_id=agent_id,
                    job_id=job_id,
                    success=True,
                    result_summary_json=json.dumps(rep) if rep else "",
                    agent_hostname=host_snapshot,
                ),
                metadata=md,
            )
        elif lease.kind == JobKind.PATH_PRECHECK.value:
            all_ok, report = path_precheck_report(list(cfg.get("paths") or []))
            report["checked_at_agent_release"] = __version__
            stub.CompleteJob(
                agent_pb2.CompleteJobRequest(
                    agent_id=agent_id,
                    job_id=job_id,
                    success=all_ok,
                    error_code="" if all_ok else "PATH_PRECHECK_FAILED",
                    error_message="" if all_ok else "one or more paths missing or not readable",
                    result_summary_json=json.dumps(report),
                    agent_hostname=host_snapshot,
                ),
                metadata=md,
            )
        else:
            raise FileBackupError("UNSUPPORTED", f"job kind {lease.kind}")
    except FileBackupError as e:
        logger.warning("job failed job_id=%s code=%s %s", job_id, e.code, e.message)
        stub.CompleteJob(
            agent_pb2.CompleteJobRequest(
                agent_id=agent_id,
                job_id=job_id,
                success=False,
                error_code=e.code,
                error_message=e.message,
                agent_hostname=host_snapshot,
            ),
            metadata=md,
        )


def run_forever() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
    )
    s = get_settings()
    target = s.grpc_target or os.environ.get("DEVAULT_GRPC_TARGET")
    if not target:
        logger.error("Set DEVAULT_GRPC_TARGET or configure DEVAULT_GRPC_TARGET in settings")
        raise SystemExit(2)

    bearer = (s.agent_token or os.environ.get("DEVAULT_AGENT_TOKEN") or "").strip()
    if not bearer:
        logger.error("Set DEVAULT_AGENT_TOKEN or configure agent_token in settings")
        raise SystemExit(2)

    cap_state = AgentCapabilityState()
    channel = _build_channel(target, settings=s)
    stub = agent_pb2_grpc.AgentControlStub(channel)
    persisted = _load_persisted_agent_id(s)

    try:
        agent_id = _register_agent(
            stub,
            bearer=bearer,
            agent_id=persisted,
            settings=s,
            cap_state=cap_state,
        )
    except grpc.RpcError as e:
        reason = _trailing_reason_code(e)
        if e.code() in (
            grpc.StatusCode.FAILED_PRECONDITION,
            grpc.StatusCode.INVALID_ARGUMENT,
        ) and reason in _FATAL_VERSION_REASONS:
            logger.error("Register version policy (%s): %s", reason, e.details())
            raise SystemExit(2) from e
        logger.exception("Register RPC failed: %s", e.details())
        raise SystemExit(2) from e

    logger.info("DeVault agent %s running (DeVault %s)", agent_id, __version__)

    while True:
        try:
            md = _metadata(bearer)
            rel, pkg, gc = _agent_identity_fields(s)
            hb = stub.Heartbeat(
                agent_pb2.HeartbeatRequest(
                    agent_id=agent_id,
                    agent_release=rel,
                    proto_package=pkg,
                    git_commit=gc,
                ),
                metadata=md,
            )
            if hb.ok:
                cap_state.caps = frozenset(hb.server_capabilities)
            if not hb.ok:
                logger.warning("heartbeat not ok")
            if hb.deprecation_message:
                logger.warning("control plane: %s", hb.deprecation_message)
            if hb.ok and hb.server_capabilities:
                logger.info("server_capabilities: %s", sorted(hb.server_capabilities))
            leased = stub.LeaseJobs(
                agent_pb2.LeaseJobsRequest(agent_id=agent_id, max_jobs=1),
                metadata=md,
            )
            if not leased.jobs:
                time.sleep(2.0)
                continue
            for job in leased.jobs:
                _run_one_job(
                    stub,
                    agent_id,
                    job,
                    bearer,
                    server_capabilities=cap_state.caps,
                )
        except grpc.RpcError as e:
            reason = _trailing_reason_code(e)
            if e.code() in (
                grpc.StatusCode.FAILED_PRECONDITION,
                grpc.StatusCode.INVALID_ARGUMENT,
            ) and reason in _FATAL_VERSION_REASONS:
                logger.error("gRPC version policy (%s): %s", reason, e.details())
                raise SystemExit(2) from e
            logger.exception("rpc error: %s", e.details())
            time.sleep(5.0)


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] in ("--version", "-V"):
        print(__version__)
        return
    run_forever()


if __name__ == "__main__":
    main()
