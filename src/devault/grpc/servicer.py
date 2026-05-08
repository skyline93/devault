from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone

import grpc
from sqlalchemy import exists, or_, select, update
from sqlalchemy.orm import Session, aliased

from devault.core.enums import JobKind, JobStatus, PluginName
from devault.core.locking import release_policy_job_lock, try_acquire_policy_job_lock
from devault.db.models import Artifact, Job
from devault.db.session import SessionLocal
from devault.grpc.rpc_governance import grpc_governance
from devault.grpc_gen import agent_pb2, agent_pb2_grpc
from devault.observability.metrics import JOB_DURATION_SECONDS, JOB_TOTAL
from devault.plugins.file.plugin import artifact_object_keys
from devault.settings import Settings, get_settings
from devault.storage import get_storage
from devault.storage.presign import (
    presign_get_object,
    presign_put_object,
    s3_client_from_settings,
)

logger = logging.getLogger(__name__)

_ACTIVE_JOB_STATUSES = (
    JobStatus.RUNNING.value,
    JobStatus.UPLOADING.value,
    JobStatus.VERIFYING.value,
)


def _auth(context: grpc.ServicerContext, settings: Settings) -> None:
    if not settings.api_token:
        return
    meta = dict(context.invocation_metadata())
    auth = meta.get("authorization") or meta.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        context.abort(grpc.StatusCode.UNAUTHENTICATED, "Bearer token required")
        raise RuntimeError("unreachable")
    token = auth[7:].strip()
    if token != settings.api_token:
        context.abort(grpc.StatusCode.UNAUTHENTICATED, "invalid token")
        raise RuntimeError("unreachable")


def reclaim_expired_job_leases(db: Session, settings: Settings) -> None:
    now = datetime.now(timezone.utc)
    stmt = select(Job).where(
        Job.lease_expires_at.is_not(None),
        Job.lease_expires_at < now,
        Job.status.in_(_ACTIVE_JOB_STATUSES),
    )
    jobs = list(db.scalars(stmt).all())
    for job in jobs:
        if job.policy_id:
            release_policy_job_lock(
                job.policy_id,
                job.id,
                redis_url=settings.redis_url,
            )
        job.status = JobStatus.PENDING.value
        job.lease_agent_id = None
        job.lease_expires_at = None
        job.started_at = None


def _pending_candidate_ids(db: Session) -> list[uuid.UUID]:
    j_active = aliased(Job)
    stmt = (
        select(Job.id)
        .where(
            Job.status == JobStatus.PENDING.value,
            or_(
                Job.policy_id.is_(None),
                ~exists(
                    select(1)
                    .select_from(j_active)
                    .where(
                        j_active.policy_id == Job.policy_id,
                        j_active.status.in_(_ACTIVE_JOB_STATUSES),
                    )
                ),
            ),
        )
        .order_by(Job.id.asc())
        .limit(50)
    )
    return list(db.scalars(stmt).all())


def try_lease_next_job(db: Session, agent_id: uuid.UUID, settings: Settings) -> Job | None:
    for jid in _pending_candidate_ids(db):
        job = db.get(Job, jid)
        if job is None or job.status != JobStatus.PENDING.value:
            continue

        acquired_redis = False
        if job.kind == JobKind.BACKUP.value and job.policy_id:
            acquired_redis = try_acquire_policy_job_lock(
                job.policy_id,
                job.id,
                redis_url=settings.redis_url,
            )
            if not acquired_redis:
                continue

        lease_ttl = timedelta(seconds=settings.job_lease_ttl_seconds)
        now = datetime.now(timezone.utc)
        result = db.execute(
            update(Job)
            .where(Job.id == jid, Job.status == JobStatus.PENDING.value)
            .values(
                status=JobStatus.RUNNING.value,
                lease_agent_id=agent_id,
                lease_expires_at=now + lease_ttl,
                started_at=now,
            )
            .returning(Job.id)
        )
        row_id = result.scalar_one_or_none()
        if row_id:
            leased_row = db.get(Job, row_id)
            if leased_row:
                return leased_row

        if acquired_redis and job.policy_id:
            release_policy_job_lock(job.policy_id, job.id, redis_url=settings.redis_url)

    return None


def _lease_config_json(db: Session, job: Job) -> str:
    cfg = dict(job.config_snapshot or {})
    if job.kind == JobKind.RESTORE.value and job.restore_artifact_id:
        art = db.get(Artifact, job.restore_artifact_id)
        if art:
            cfg["expected_checksum_sha256"] = art.checksum_sha256
    return json.dumps(cfg)


class AgentControlServicer(agent_pb2_grpc.AgentControlServicer):
    def Register(self, request: agent_pb2.RegisterRequest, context: grpc.ServicerContext):
        settings = get_settings()
        with grpc_governance(
            "Register",
            context,
            settings,
            audit_extra={"agent_id": request.agent_id},
        ):
            if not settings.grpc_registration_secret:
                context.abort(grpc.StatusCode.FAILED_PRECONDITION, "registration disabled")
            if request.registration_secret != settings.grpc_registration_secret:
                context.abort(grpc.StatusCode.UNAUTHENTICATED, "invalid registration secret")
            try:
                uuid.UUID(request.agent_id)
            except ValueError:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "agent_id must be a UUID")
            if not settings.api_token:
                return agent_pb2.RegisterReply(
                    ok=False,
                    message="DEVAULT_API_TOKEN not configured on control plane",
                    expires_in_seconds=0,
                )
            return agent_pb2.RegisterReply(
                ok=True,
                bearer_token=settings.api_token,
                expires_in_seconds=0,
                message="ok",
            )

    def Heartbeat(self, request: agent_pb2.HeartbeatRequest, context: grpc.ServicerContext):
        settings = get_settings()
        with grpc_governance(
            "Heartbeat",
            context,
            settings,
            audit_extra={"agent_id": request.agent_id},
        ):
            _auth(context, settings)
            return agent_pb2.HeartbeatReply(ok=True)

    def LeaseJobs(
        self,
        request: agent_pb2.LeaseJobsRequest,
        context: grpc.ServicerContext,
    ):
        settings = get_settings()
        with grpc_governance(
            "LeaseJobs",
            context,
            settings,
            audit_extra={"agent_id": request.agent_id},
        ):
            _auth(context, settings)
            try:
                agent_uuid = uuid.UUID(request.agent_id)
            except ValueError:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "agent_id must be a UUID")
                raise

            max_jobs = min(max(int(request.max_jobs or 1), 1), 10)
            db = SessionLocal()
            leases: list[agent_pb2.JobLease] = []
            try:
                reclaim_expired_job_leases(db, settings)
                for _ in range(max_jobs):
                    job = try_lease_next_job(db, agent_uuid, settings)
                    if job is None:
                        break
                    leases.append(
                        agent_pb2.JobLease(
                            job_id=str(job.id),
                            kind=job.kind,
                            plugin=job.plugin,
                            config_json=_lease_config_json(db, job),
                        )
                    )
                db.commit()
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()

            return agent_pb2.LeaseJobsReply(jobs=leases)

    def RequestStorageGrant(
        self,
        request: agent_pb2.RequestStorageGrantRequest,
        context: grpc.ServicerContext,
    ):
        settings = get_settings()
        with grpc_governance(
            "RequestStorageGrant",
            context,
            settings,
            audit_extra={"agent_id": request.agent_id, "job_id": request.job_id},
        ):
            _auth(context, settings)
            if settings.storage_backend != "s3":
                context.abort(
                    grpc.StatusCode.FAILED_PRECONDITION,
                    "Agent storage grants require DEVAULT_STORAGE_BACKEND=s3 on control plane",
                )
                raise RuntimeError("unreachable")

            try:
                agent_uuid = uuid.UUID(request.agent_id)
                job_uuid = uuid.UUID(request.job_id)
            except ValueError:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "invalid UUID")
                raise

            db = SessionLocal()
            try:
                job = db.get(Job, job_uuid)
                if job is None:
                    context.abort(grpc.StatusCode.NOT_FOUND, "job not found")
                    raise RuntimeError("unreachable")
                if job.lease_agent_id != agent_uuid:
                    context.abort(grpc.StatusCode.PERMISSION_DENIED, "job not leased to this agent")
                    raise RuntimeError("unreachable")
                if job.status not in _ACTIVE_JOB_STATUSES:
                    context.abort(grpc.StatusCode.FAILED_PRECONDITION, "job not active")

                ttl = int(settings.presign_ttl_seconds)
                client = s3_client_from_settings(settings)
                bucket = settings.s3_bucket

                if request.intent == agent_pb2.STORAGE_INTENT_WRITE:
                    if job.kind != JobKind.BACKUP.value:
                        context.abort(grpc.StatusCode.INVALID_ARGUMENT, "WRITE only for backup jobs")
                    bundle_key, manifest_key = artifact_object_keys(settings, job.id)
                    reply = agent_pb2.RequestStorageGrantReply(
                        bundle_key=bundle_key,
                        manifest_key=manifest_key,
                        bundle_http_url=presign_put_object(
                            client, bucket=bucket, key=bundle_key, expires_in=ttl
                        ),
                        manifest_http_url=presign_put_object(
                            client, bucket=bucket, key=manifest_key, expires_in=ttl
                        ),
                        expires_in_seconds=ttl,
                    )
                    job.status = JobStatus.UPLOADING.value
                    db.commit()
                    return reply

                if request.intent == agent_pb2.STORAGE_INTENT_READ:
                    if job.kind != JobKind.RESTORE.value:
                        context.abort(grpc.StatusCode.INVALID_ARGUMENT, "READ only for restore jobs")
                    aid = job.restore_artifact_id
                    if aid is None:
                        context.abort(
                            grpc.StatusCode.FAILED_PRECONDITION,
                            "restore artifact missing",
                        )
                    art = db.get(Artifact, aid)
                    if art is None:
                        context.abort(grpc.StatusCode.NOT_FOUND, "artifact not found")
                    reply = agent_pb2.RequestStorageGrantReply(
                        bundle_key=art.bundle_key,
                        manifest_key=art.manifest_key,
                        bundle_http_url=presign_get_object(
                            client, bucket=bucket, key=art.bundle_key, expires_in=ttl
                        ),
                        manifest_http_url="",
                        expires_in_seconds=ttl,
                        expected_checksum_sha256=art.checksum_sha256,
                    )
                    db.commit()
                    return reply

                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "intent required")
                raise RuntimeError("unreachable")
            finally:
                db.close()

    def ReportProgress(
        self,
        request: agent_pb2.ReportProgressRequest,
        context: grpc.ServicerContext,
    ):
        settings = get_settings()
        with grpc_governance(
            "ReportProgress",
            context,
            settings,
            audit_extra={"agent_id": request.agent_id, "job_id": request.job_id},
        ):
            _auth(context, settings)
            try:
                agent_uuid = uuid.UUID(request.agent_id)
                job_uuid = uuid.UUID(request.job_id)
            except ValueError:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "invalid UUID")
                raise

            db = SessionLocal()
            try:
                job = db.get(Job, job_uuid)
                cancelled = bool(job and job.status == JobStatus.CANCELLED.value)
                if job and job.lease_agent_id == agent_uuid and not cancelled:
                    if request.percent >= 90:
                        job.status = JobStatus.VERIFYING.value
                db.commit()
                return agent_pb2.ReportProgressReply(ok=True, job_cancelled=cancelled)
            finally:
                db.close()

    def CompleteJob(
        self,
        request: agent_pb2.CompleteJobRequest,
        context: grpc.ServicerContext,
    ):
        settings = get_settings()
        with grpc_governance(
            "CompleteJob",
            context,
            settings,
            audit_extra={"agent_id": request.agent_id, "job_id": request.job_id},
        ):
            _auth(context, settings)
            try:
                agent_uuid = uuid.UUID(request.agent_id)
                job_uuid = uuid.UUID(request.job_id)
            except ValueError:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "invalid UUID")
                raise

            t_inner = time.monotonic()
            db = SessionLocal()
            try:
                job = db.get(Job, job_uuid)
                if job is None:
                    context.abort(grpc.StatusCode.NOT_FOUND, "job not found")
                    raise RuntimeError("unreachable")
                if job.lease_agent_id != agent_uuid:
                    context.abort(grpc.StatusCode.PERMISSION_DENIED, "job not leased to this agent")
                    raise RuntimeError("unreachable")

                if request.success:
                    if job.kind == JobKind.BACKUP.value:
                        storage = get_storage(settings)
                        bundle_key = request.bundle_key or ""
                        manifest_key = request.manifest_key or ""
                        if not bundle_key or not manifest_key:
                            context.abort(
                                grpc.StatusCode.INVALID_ARGUMENT,
                                "bundle/manifest keys required",
                            )
                        if not storage.exists(bundle_key) or not storage.exists(manifest_key):
                            context.abort(
                                grpc.StatusCode.FAILED_PRECONDITION,
                                "artifact objects missing",
                            )
                        art = Artifact(
                            job_id=job.id,
                            storage_backend=storage.backend_name,
                            bundle_key=bundle_key,
                            manifest_key=manifest_key,
                            size_bytes=int(request.size_bytes),
                            checksum_sha256=request.checksum_sha256,
                            compression="tar.gz",
                            encrypted=False,
                        )
                        db.add(art)
                        job.status = JobStatus.SUCCESS.value
                        job.finished_at = datetime.now(timezone.utc)
                        JOB_TOTAL.labels(kind="backup", plugin=job.plugin, status="success").inc()
                    else:
                        job.status = JobStatus.SUCCESS.value
                        job.finished_at = datetime.now(timezone.utc)
                        JOB_TOTAL.labels(kind="restore", plugin=job.plugin, status="success").inc()
                else:
                    job.status = JobStatus.FAILED.value
                    job.error_code = (request.error_code or "FAILED")[:64]
                    job.error_message = (request.error_message or "")[:8000]
                    job.finished_at = datetime.now(timezone.utc)
                    JOB_TOTAL.labels(
                        kind=job.kind,
                        plugin=job.plugin,
                        status="failed",
                    ).inc()

                job.lease_agent_id = None
                job.lease_expires_at = None

                if job.policy_id:
                    release_policy_job_lock(
                        job.policy_id,
                        job.id,
                        redis_url=settings.redis_url,
                    )

                db.commit()
                JOB_DURATION_SECONDS.labels(kind=job.kind, plugin=PluginName.FILE.value).observe(
                    time.monotonic() - t_inner
                )
                return agent_pb2.CompleteJobReply(ok=True)
            finally:
                db.close()
