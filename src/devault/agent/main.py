from __future__ import annotations

import json
import logging
import os
import shutil
import sys
import time
import uuid
from pathlib import Path
from types import SimpleNamespace

import grpc

from devault import __version__
from devault.core.enums import JobKind
from devault.grpc_gen import agent_pb2, agent_pb2_grpc
from devault.plugins.file import FileBackupError, run_file_restore_with_presigned_bundle
from devault.plugins.file.multipart_wip import (
    bundle_wip_path,
    checkpoint_path,
    clear_job_multipart_state,
)
from devault.plugins.file.plugin import (
    BackupOutcome,
    _build_backup_tarball,
    artifact_object_keys,
    upload_backup_via_storage_grant,
    write_multipart_checkpoint,
)
from devault.settings import Settings, get_settings

logger = logging.getLogger(__name__)


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


def _bootstrap_token_if_needed(stub: agent_pb2_grpc.AgentControlStub, agent_id: str, token: dict) -> None:
    if token.get("value"):
        return
    s = get_settings()
    if s.api_token:
        token["value"] = s.api_token
        return
    if not s.grpc_registration_secret:
        logger.error(
            "No DEVAULT_API_TOKEN and no DEVAULT_GRPC_REGISTRATION_SECRET; cannot authenticate",
        )
        raise SystemExit(2)
    reply = stub.Register(
        agent_pb2.RegisterRequest(
            agent_id=agent_id,
            registration_secret=s.grpc_registration_secret,
        ),
        metadata=[],
    )
    if not reply.ok or not reply.bearer_token:
        logger.error("Register failed: %s", reply.message or "unknown")
        raise SystemExit(2)
    token["value"] = reply.bearer_token
    logger.info("obtained API token via Register (bootstrap)")


def _run_one_job(
    stub: agent_pb2_grpc.AgentControlStub,
    agent_id: str,
    lease: agent_pb2.JobLease,
    bearer: str,
) -> None:
    s = get_settings()
    job_id = lease.job_id
    md = _metadata(bearer)
    cfg = json.loads(lease.config_json)
    try:
        if lease.kind == JobKind.BACKUP.value:
            job_stub = _job_view(job_id, lease, cfg)
            bid = uuid.UUID(job_id)
            bundle_key, manifest_key = artifact_object_keys(s, bid)
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

            if resume_upload_id and wip_bundle.is_file() and ck_data is not None:
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
                if size_bytes >= int(s.s3_multipart_threshold_bytes):
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
        elif lease.kind == JobKind.RESTORE.value:
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
            run_file_restore_with_presigned_bundle(
                job=job_stub,
                settings=s,
                bundle_get_url=g.bundle_http_url,
                expected_checksum_sha256=expected,
            )
            stub.CompleteJob(
                agent_pb2.CompleteJobRequest(agent_id=agent_id, job_id=job_id, success=True),
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

    agent_id = os.environ.get("DEVAULT_AGENT_ID") or str(uuid.uuid4())
    logger.info("DeVault agent %s starting (DeVault %s)", agent_id, __version__)

    token: dict[str, str | None] = {"value": None}
    channel = _build_channel(target, settings=s)
    stub = agent_pb2_grpc.AgentControlStub(channel)

    try:
        _bootstrap_token_if_needed(stub, agent_id, token)
    except grpc.RpcError as e:
        logger.exception("Register RPC failed: %s", e.details())
        raise SystemExit(2) from e

    bearer = token["value"]
    if not bearer:
        logger.error("No bearer token after bootstrap")
        raise SystemExit(2)

    while True:
        try:
            md = _metadata(bearer)
            hb = stub.Heartbeat(
                agent_pb2.HeartbeatRequest(agent_id=agent_id),
                metadata=md,
            )
            if not hb.ok:
                logger.warning("heartbeat not ok")
            leased = stub.LeaseJobs(
                agent_pb2.LeaseJobsRequest(agent_id=agent_id, max_jobs=1),
                metadata=md,
            )
            if not leased.jobs:
                time.sleep(2.0)
                continue
            for job in leased.jobs:
                _run_one_job(stub, agent_id, job, bearer)
        except grpc.RpcError as e:
            logger.exception("rpc error: %s", e.details())
            time.sleep(5.0)


def main() -> None:
    run_forever()


if __name__ == "__main__":
    main()
