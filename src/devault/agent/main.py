from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from types import SimpleNamespace

import grpc

from devault import __version__
from devault.core.enums import JobKind
from devault.grpc_gen import agent_pb2, agent_pb2_grpc
from devault.plugins.file import (
    FileBackupError,
    run_file_backup_with_presigned_urls,
    run_file_restore_with_presigned_bundle,
)
from devault.settings import get_settings

logger = logging.getLogger(__name__)


def _metadata() -> list[tuple[str, str]]:
    s = get_settings()
    if not s.api_token:
        return []
    return [("authorization", f"Bearer {s.api_token}")]


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


def _run_one_job(
    stub: agent_pb2_grpc.AgentControlStub,
    agent_id: str,
    lease: agent_pb2.JobLease,
) -> None:
    s = get_settings()
    job_id = lease.job_id
    md = _metadata()
    cfg = json.loads(lease.config_json)
    try:
        if lease.kind == JobKind.BACKUP.value:
            g = stub.RequestStorageGrant(
                agent_pb2.RequestStorageGrantRequest(
                    agent_id=agent_id,
                    job_id=job_id,
                    intent=agent_pb2.STORAGE_INTENT_WRITE,
                ),
                metadata=md,
            )
            job_stub = _job_view(job_id, lease, cfg)
            outcome = run_file_backup_with_presigned_urls(
                job=job_stub,
                settings=s,
                bundle_put_url=g.bundle_http_url,
                manifest_put_url=g.manifest_http_url,
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
                ),
                metadata=md,
            )
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

    channel = grpc.insecure_channel(target)
    stub = agent_pb2_grpc.AgentControlStub(channel)

    while True:
        try:
            md = _metadata()
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
                _run_one_job(stub, agent_id, job)
        except grpc.RpcError as e:
            logger.exception("rpc error: %s", e.details())
            time.sleep(5.0)


def main() -> None:
    run_forever()


if __name__ == "__main__":
    main()
