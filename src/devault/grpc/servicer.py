from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone

import grpc
from botocore.exceptions import ClientError
from sqlalchemy import and_, exists, or_, select, update
from sqlalchemy.orm import Session, aliased

from devault import __version__ as server_release_version
from devault.core.enums import JobKind, JobStatus, PluginName
from devault.core.locking import release_policy_job_lock, try_acquire_policy_job_lock
from devault.db.models import Artifact, EdgeAgent, Job, Policy, StorageProfile, Tenant
from devault.db.session import SessionLocal
from devault.security.agent_token_auth import (
    auth_context_from_agent_token,
    ensure_agent_instance_for_token,
    require_agent_token,
)
from devault.security.auth_context import AuthContext, dev_open_auth_context
from devault.security.policy import authentication_enabled
from devault.grpc.agent_version import (
    attach_control_plane_version_meta,
    evaluate_agent_version_gate,
)
from devault.server_capabilities import apply_server_capabilities
from devault.grpc.rpc_governance import grpc_governance
from devault.grpc_gen import agent_pb2, agent_pb2_grpc
from devault.observability.metrics import (
    BACKUP_INTEGRITY_CONTROL_REJECTS_TOTAL,
    BILLING_COMMITTED_BYTES_TOTAL,
    JOB_DURATION_SECONDS,
    JOB_TOTAL,
    MULTIPART_ENCRYPTED_MPU_COMPLETES_TOTAL,
    MULTIPART_RESUME_GRANTS_TOTAL,
    agent_error_class,
    job_terminal_label_values,
)
from devault.retention.policy import retain_until_from_backup_config
from devault.grpc.object_lock_params import object_lock_params_from_backup_cfg
from devault.plugins.file.encryption_policy import (
    encryption_required,
    manifest_declares_chunked_encryption,
)
from devault.plugins.file.plugin import artifact_object_keys
from devault.services.edge_agents import (
    enforce_edge_agent_for_lease,
    touch_edge_agent_heartbeat,
    upsert_edge_agent,
)
from devault.settings import Settings, get_settings
from devault.services.storage_profiles import get_active_profile, require_active_profile, s3_conn_spec_from_profile
from devault.storage import get_storage_for_active_profile, get_storage_for_artifact_row, get_storage_for_profile
from devault.storage.multipart import (
    abort_multipart_upload_best_effort,
    build_multipart_part_presigns,
    build_multipart_part_presigns_missing,
    effective_part_size_bytes,
    list_uploaded_multipart_parts,
    multipart_upload_is_complete,
    start_multipart_upload,
)
from devault.storage.presign import presign_get_object, presign_put_object
from devault.storage.s3 import S3Storage
from devault.storage.s3_client import build_s3_client_from_spec

logger = logging.getLogger(__name__)

_ACTIVE_JOB_STATUSES = (
    JobStatus.RUNNING.value,
    JobStatus.UPLOADING.value,
    JobStatus.VERIFYING.value,
)


def _grpc_bearer_raw(context: grpc.ServicerContext) -> str:
    meta = dict(context.invocation_metadata())
    auth = meta.get("authorization") or meta.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        return ""
    return auth[7:].strip()


def _authenticate_grpc(context: grpc.ServicerContext, settings: Settings) -> AuthContext:
    db = SessionLocal()
    try:
        if not authentication_enabled(settings, db):
            return dev_open_auth_context()
        raw = _grpc_bearer_raw(context)
        if not raw:
            context.abort(grpc.StatusCode.UNAUTHENTICATED, "Bearer token required")
            raise RuntimeError("unreachable")
        principal = require_agent_token(db, context, raw)
        db.commit()
        return auth_context_from_agent_token(principal)
    finally:
        db.close()


def _agent_token_id_from_auth(auth_ctx: AuthContext) -> uuid.UUID | None:
    label = auth_ctx.principal_label
    prefix = "agent-token:"
    if not label.startswith(prefix):
        return None
    try:
        return uuid.UUID(label[len(prefix) :])
    except ValueError:
        return None


def _grpc_ensure_job_tenant(
    auth_ctx: AuthContext,
    tenant_id: uuid.UUID,
    context: grpc.ServicerContext,
) -> None:
    """Reject cross-tenant job access for scoped principals (Register token or scoped API key)."""
    if auth_ctx.allowed_tenant_ids is None:
        return
    if tenant_id not in auth_ctx.allowed_tenant_ids:
        context.abort(
            grpc.StatusCode.PERMISSION_DENIED,
            "principal is not allowed for this job's tenant",
        )
        raise RuntimeError("unreachable")


def _require_agent_bearer_matches(
    auth_ctx: AuthContext,
    agent_id: uuid.UUID,
    context: grpc.ServicerContext,
) -> None:
    """Agent token principals may only use registered ``agent_id`` values for that token."""
    token_id = _agent_token_id_from_auth(auth_ctx)
    if token_id is None:
        return
    db = SessionLocal()
    try:
        ensure_agent_instance_for_token(db, agent_id=agent_id, token_id=token_id, context=context)
    finally:
        db.close()


def _resolved_complete_agent_hostname(
    db: Session,
    agent_uuid: uuid.UUID,
    request: agent_pb2.CompleteJobRequest,
) -> str | None:
    raw = (request.agent_hostname or "").strip()
    if raw:
        return raw[:255]
    row = db.get(EdgeAgent, agent_uuid)
    if row and row.hostname:
        h = (row.hostname or "").strip()
        return h[:255] if h else None
    return None


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
        job.lease_agent_hostname = None
        job.lease_expires_at = None
        job.started_at = None


def _pending_candidate_ids(
    db: Session,
    auth_allowed: frozenset[uuid.UUID] | None,
    leasing_agent_id: uuid.UUID,
) -> list[uuid.UUID]:
    if auth_allowed is not None and len(auth_allowed) == 0:
        return []
    j_active = aliased(Job)
    policy_binding_ok = or_(
        Job.policy_id.is_(None),
        exists(
            select(1).select_from(Policy).where(
                Policy.id == Job.policy_id,
                Policy.bound_agent_id == leasing_agent_id,
            ),
        ),
    )
    stmt = (
        select(Job.id)
        .where(
            Job.status == JobStatus.PENDING.value,
            policy_binding_ok,
            or_(
                Job.policy_id.is_(None),
                ~exists(
                    select(1)
                    .select_from(j_active)
                    .where(
                        j_active.policy_id == Job.policy_id,
                        j_active.status.in_(_ACTIVE_JOB_STATUSES),
                        j_active.kind == JobKind.BACKUP.value,
                    )
                ),
            ),
        )
        .order_by(Job.created_at.asc())
        .limit(50)
    )
    if auth_allowed is not None:
        stmt = stmt.where(Job.tenant_id.in_(auth_allowed))
    return list(db.scalars(stmt).all())


def try_lease_next_job(
    db: Session,
    agent_id: uuid.UUID,
    settings: Settings,
    auth_allowed: frozenset[uuid.UUID] | None,
) -> Job | None:
    for jid in _pending_candidate_ids(db, auth_allowed, agent_id):
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
        lease_host: str | None = None
        edge_row = db.get(EdgeAgent, agent_id)
        if edge_row and edge_row.hostname:
            lease_host = (edge_row.hostname or "").strip()[:255] or None
        result = db.execute(
            update(Job)
            .where(Job.id == jid, Job.status == JobStatus.PENDING.value)
            .values(
                status=JobStatus.RUNNING.value,
                lease_agent_id=agent_id,
                lease_agent_hostname=lease_host,
                lease_expires_at=now + lease_ttl,
                started_at=now,
            )
            .returning(Job.id)
        )
        row_id = result.scalar_one_or_none()
        if row_id:
            leased_row = db.get(Job, row_id)
            if leased_row:
                db.refresh(leased_row)
                return leased_row

        if acquired_redis and job.policy_id:
            release_policy_job_lock(job.policy_id, job.id, redis_url=settings.redis_url)

    return None


def _lease_config_json(db: Session, job: Job) -> str:
    cfg = dict(job.config_snapshot or {})
    cfg["tenant_id"] = str(job.tenant_id)
    tenant = db.get(Tenant, job.tenant_id)
    if tenant and tenant.kms_envelope_key_id:
        cfg.setdefault("kms_envelope_key_id", tenant.kms_envelope_key_id)
    if job.kind in (JobKind.RESTORE.value, JobKind.RESTORE_DRILL.value) and job.restore_artifact_id:
        art = db.get(Artifact, job.restore_artifact_id)
        if art:
            cfg["expected_checksum_sha256"] = art.checksum_sha256
            cfg["artifact_encrypted"] = bool(art.encrypted)
    return json.dumps(cfg)


class AgentControlServicer(agent_pb2_grpc.AgentControlServicer):
    def Register(self, request: agent_pb2.RegisterRequest, context: grpc.ServicerContext):
        settings = get_settings()
        register_audit: dict = {
            "agent_id": request.agent_id or None,
            "agent_release": request.agent_release or None,
            "proto_package": request.proto_package or None,
            "agent_git_commit": request.git_commit or None,
        }
        with grpc_governance(
            "Register",
            context,
            settings,
            audit_extra=register_audit,
        ):
            raw = _grpc_bearer_raw(context)
            db_reg = SessionLocal()
            try:
                principal = require_agent_token(db_reg, context, raw)
                token_id = principal.token.id
                register_audit["agent_token_id"] = str(token_id)
                register_audit["tenant_id"] = str(principal.tenant_id)
                dep = evaluate_agent_version_gate(
                    agent_release=request.agent_release,
                    proto_package=request.proto_package,
                    settings=settings,
                    context=context,
                    server_release=server_release_version,
                )
                agent_uuid: uuid.UUID
                if (request.agent_id or "").strip():
                    try:
                        agent_uuid = uuid.UUID(request.agent_id)
                    except ValueError:
                        context.abort(grpc.StatusCode.INVALID_ARGUMENT, "agent_id must be a UUID")
                        raise
                    existing = db_reg.get(EdgeAgent, agent_uuid)
                    if existing is not None and existing.agent_token_id not in (None, token_id):
                        context.abort(
                            grpc.StatusCode.PERMISSION_DENIED,
                            "agent_id is registered to a different token",
                        )
                        raise RuntimeError("unreachable")
                else:
                    agent_uuid = uuid.uuid4()
                snap_ver = int(request.snapshot_schema_version or 0)
                upsert_edge_agent(
                    db_reg,
                    agent_id=agent_uuid,
                    agent_token_id=token_id,
                    agent_release=request.agent_release or None,
                    proto_package=request.proto_package or None,
                    git_commit=request.git_commit or None,
                    touch_register=True,
                    snapshot_schema_version=snap_ver,
                    hostname=request.hostname or None,
                    host_os=request.os or None,
                    region=request.region or None,
                    agent_env=request.env or None,
                    backup_path_allowlist=list(request.backup_path_allowlist),
                )
                db_reg.commit()
            finally:
                db_reg.close()
            reply = agent_pb2.RegisterReply(
                ok=True,
                message="ok",
                deprecation_message=dep,
                agent_id=str(agent_uuid),
            )
            attach_control_plane_version_meta(reply, settings)
            apply_server_capabilities(reply, settings)
            return reply

    def Heartbeat(self, request: agent_pb2.HeartbeatRequest, context: grpc.ServicerContext):
        settings = get_settings()
        hb_audit: dict = {
            "agent_id": request.agent_id,
            "agent_release": request.agent_release or None,
            "proto_package": request.proto_package or None,
            "agent_git_commit": request.git_commit or None,
        }
        with grpc_governance(
            "Heartbeat",
            context,
            settings,
            audit_extra=hb_audit,
        ):
            auth_ctx = _authenticate_grpc(context, settings)
            try:
                hb_agent = uuid.UUID(request.agent_id)
            except ValueError:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "agent_id must be a UUID")
                raise
            _require_agent_bearer_matches(auth_ctx, hb_agent, context)
            dep = evaluate_agent_version_gate(
                agent_release=request.agent_release,
                proto_package=request.proto_package,
                settings=settings,
                context=context,
                server_release=server_release_version,
            )
            db_hb = SessionLocal()
            try:
                touch_edge_agent_heartbeat(
                    db_hb,
                    agent_id=hb_agent,
                    agent_release=request.agent_release or None,
                    proto_package=request.proto_package or None,
                    git_commit=request.git_commit or None,
                )
                db_hb.commit()
            finally:
                db_hb.close()
            reply = agent_pb2.HeartbeatReply(ok=True, deprecation_message=dep)
            attach_control_plane_version_meta(reply, settings)
            apply_server_capabilities(reply, settings)
            return reply

    def LeaseJobs(
        self,
        request: agent_pb2.LeaseJobsRequest,
        context: grpc.ServicerContext,
    ):
        settings = get_settings()
        lease_audit: dict = {"agent_id": request.agent_id}
        with grpc_governance(
            "LeaseJobs",
            context,
            settings,
            audit_extra=lease_audit,
        ):
            auth_ctx = _authenticate_grpc(context, settings)
            try:
                agent_uuid = uuid.UUID(request.agent_id)
            except ValueError:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "agent_id must be a UUID")
                raise
            _require_agent_bearer_matches(auth_ctx, agent_uuid, context)
            if auth_ctx.allowed_tenant_ids is None:
                lease_audit["tenant_scope"] = "all"
            else:
                lease_audit["tenant_scope"] = "restricted"
                lease_audit["allowed_tenant_count"] = len(auth_ctx.allowed_tenant_ids)

            max_jobs = min(max(int(request.max_jobs or 1), 1), 10)
            db = SessionLocal()
            leases: list[agent_pb2.JobLease] = []
            try:
                reclaim_expired_job_leases(db, settings)
                enforce_edge_agent_for_lease(
                    db,
                    agent_id=agent_uuid,
                    settings=settings,
                    context=context,
                    server_release=server_release_version,
                )
                for _ in range(max_jobs):
                    job = try_lease_next_job(db, agent_uuid, settings, auth_ctx.allowed_tenant_ids)
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
        grant_audit: dict = {"agent_id": request.agent_id, "job_id": request.job_id}
        with grpc_governance(
            "RequestStorageGrant",
            context,
            settings,
            audit_extra=grant_audit,
        ):
            auth_ctx = _authenticate_grpc(context, settings)
            try:
                agent_uuid = uuid.UUID(request.agent_id)
                job_uuid = uuid.UUID(request.job_id)
            except ValueError:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "invalid UUID")
                raise
            _require_agent_bearer_matches(auth_ctx, agent_uuid, context)

            db = SessionLocal()
            try:
                prof_gate = get_active_profile(db)
                if prof_gate is None or prof_gate.storage_type != "s3":
                    context.abort(
                        grpc.StatusCode.FAILED_PRECONDITION,
                        "Agent storage grants require an active S3 storage profile on the control plane",
                    )
                    raise RuntimeError("unreachable")

                job = db.get(Job, job_uuid)
                if job is None:
                    context.abort(grpc.StatusCode.NOT_FOUND, "job not found")
                    raise RuntimeError("unreachable")
                grant_audit["tenant_id"] = str(job.tenant_id)
                _grpc_ensure_job_tenant(auth_ctx, job.tenant_id, context)
                if job.lease_agent_id != agent_uuid:
                    context.abort(grpc.StatusCode.PERMISSION_DENIED, "job not leased to this agent")
                    raise RuntimeError("unreachable")
                if job.status not in _ACTIVE_JOB_STATUSES:
                    context.abort(grpc.StatusCode.FAILED_PRECONDITION, "job not active")

                ttl = int(settings.presign_ttl_seconds)
                ol_mode, ol_until = object_lock_params_from_backup_cfg(job.config_snapshot)

                if request.intent == agent_pb2.STORAGE_INTENT_WRITE:
                    if job.kind != JobKind.BACKUP.value:
                        context.abort(grpc.StatusCode.INVALID_ARGUMENT, "WRITE only for backup jobs")
                    try:
                        active = require_active_profile(db)
                        write_spec = s3_conn_spec_from_profile(active, settings)
                    except ValueError as e:
                        context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(e))
                        raise RuntimeError("unreachable") from e
                    client = build_s3_client_from_spec(settings, write_spec)
                    bucket = write_spec.bucket
                    bundle_key, manifest_key = artifact_object_keys(settings, job.id, job.tenant_id)
                    manifest_url = presign_put_object(
                        client,
                        bucket=bucket,
                        key=manifest_key,
                        expires_in=ttl,
                        object_lock_mode=ol_mode,
                        object_lock_retain_until=ol_until,
                    )
                    blen = int(request.bundle_content_length or 0)
                    resume_id = (request.resume_bundle_multipart_upload_id or "").strip()
                    threshold = int(settings.s3_multipart_threshold_bytes)
                    cfg_ps = int(settings.s3_multipart_part_size_bytes)

                    if blen >= threshold:
                        eff_ps = effective_part_size_bytes(blen, cfg_ps)
                        if resume_id:
                            if not job.bundle_wip_multipart_upload_id:
                                context.abort(
                                    grpc.StatusCode.INVALID_ARGUMENT,
                                    "no in-progress multipart upload for this job",
                                )
                                raise RuntimeError("unreachable")
                            if resume_id != job.bundle_wip_multipart_upload_id:
                                context.abort(
                                    grpc.StatusCode.INVALID_ARGUMENT,
                                    "resume_bundle_multipart_upload_id does not match job WIP",
                                )
                                raise RuntimeError("unreachable")
                            if job.bundle_wip_content_length != blen or job.bundle_wip_part_size_bytes != eff_ps:
                                context.abort(
                                    grpc.StatusCode.INVALID_ARGUMENT,
                                    "multipart resume dimensions mismatch",
                                )
                                raise RuntimeError("unreachable")
                            uploaded = list_uploaded_multipart_parts(
                                client, bucket=bucket, key=bundle_key, upload_id=resume_id
                            )
                            if multipart_upload_is_complete(
                                content_length=blen,
                                configured_part_size=cfg_ps,
                                uploaded=uploaded,
                            ):
                                reply = agent_pb2.RequestStorageGrantReply(
                                    bundle_key=bundle_key,
                                    manifest_key=manifest_key,
                                    bundle_http_url="",
                                    manifest_http_url=manifest_url,
                                    expires_in_seconds=ttl,
                                    bundle_multipart_upload_id=resume_id,
                                    bundle_multipart_parts=[],
                                    bundle_multipart_part_size_bytes=eff_ps,
                                    bundle_multipart_completed_parts_json=json.dumps(uploaded),
                                )
                            else:
                                done_nums = {int(p["PartNumber"]) for p in uploaded}
                                pairs = build_multipart_part_presigns_missing(
                                    client,
                                    bucket=bucket,
                                    key=bundle_key,
                                    upload_id=resume_id,
                                    content_length=blen,
                                    part_size=cfg_ps,
                                    expires_in=ttl,
                                    skip_part_numbers=done_nums,
                                )
                                MULTIPART_RESUME_GRANTS_TOTAL.inc()
                                reply = agent_pb2.RequestStorageGrantReply(
                                    bundle_key=bundle_key,
                                    manifest_key=manifest_key,
                                    bundle_http_url="",
                                    manifest_http_url=manifest_url,
                                    expires_in_seconds=ttl,
                                    bundle_multipart_upload_id=resume_id,
                                    bundle_multipart_parts=[
                                        agent_pb2.BundlePartPresign(part_number=a, http_put_url=b)
                                        for a, b in pairs
                                    ],
                                    bundle_multipart_part_size_bytes=eff_ps,
                                )
                        else:
                            if job.bundle_wip_multipart_upload_id:
                                abort_multipart_upload_best_effort(
                                    client,
                                    bucket=bucket,
                                    key=bundle_key,
                                    upload_id=job.bundle_wip_multipart_upload_id,
                                )
                                job.bundle_wip_multipart_upload_id = None
                                job.bundle_wip_content_length = None
                                job.bundle_wip_part_size_bytes = None
                                db.flush()

                            upload_id = start_multipart_upload(
                                client,
                                bucket=bucket,
                                key=bundle_key,
                                object_lock_mode=ol_mode,
                                object_lock_retain_until=ol_until,
                            )
                            job.bundle_wip_multipart_upload_id = upload_id
                            job.bundle_wip_content_length = blen
                            job.bundle_wip_part_size_bytes = eff_ps
                            pairs = build_multipart_part_presigns(
                                client,
                                bucket=bucket,
                                key=bundle_key,
                                upload_id=upload_id,
                                content_length=blen,
                                part_size=cfg_ps,
                                expires_in=ttl,
                            )
                            reply = agent_pb2.RequestStorageGrantReply(
                                bundle_key=bundle_key,
                                manifest_key=manifest_key,
                                bundle_http_url="",
                                manifest_http_url=manifest_url,
                                expires_in_seconds=ttl,
                                bundle_multipart_upload_id=upload_id,
                                bundle_multipart_parts=[
                                    agent_pb2.BundlePartPresign(part_number=a, http_put_url=b)
                                    for a, b in pairs
                                ],
                                bundle_multipart_part_size_bytes=eff_ps,
                            )
                    else:
                        if job.bundle_wip_multipart_upload_id:
                            abort_multipart_upload_best_effort(
                                client,
                                bucket=bucket,
                                key=bundle_key,
                                upload_id=job.bundle_wip_multipart_upload_id,
                            )
                            job.bundle_wip_multipart_upload_id = None
                            job.bundle_wip_content_length = None
                            job.bundle_wip_part_size_bytes = None
                            db.flush()
                        reply = agent_pb2.RequestStorageGrantReply(
                            bundle_key=bundle_key,
                            manifest_key=manifest_key,
                            bundle_http_url=presign_put_object(
                                client,
                                bucket=bucket,
                                key=bundle_key,
                                expires_in=ttl,
                                object_lock_mode=ol_mode,
                                object_lock_retain_until=ol_until,
                            ),
                            manifest_http_url=manifest_url,
                            expires_in_seconds=ttl,
                        )
                    job.status = JobStatus.UPLOADING.value
                    db.commit()
                    return reply

                if request.intent == agent_pb2.STORAGE_INTENT_READ:
                    if job.kind not in (JobKind.RESTORE.value, JobKind.RESTORE_DRILL.value):
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
                    if art.tenant_id != job.tenant_id:
                        context.abort(
                            grpc.StatusCode.FAILED_PRECONDITION,
                            "restore artifact tenant does not match job tenant",
                        )
                        raise RuntimeError("unreachable")
                    if art.storage_profile_id is None:
                        try:
                            prof = require_active_profile(db)
                        except ValueError as e:
                            context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(e))
                            raise RuntimeError("unreachable") from e
                    else:
                        prof = db.get(StorageProfile, art.storage_profile_id)
                        if prof is None:
                            context.abort(grpc.StatusCode.NOT_FOUND, "artifact storage profile missing")
                            raise RuntimeError("unreachable")
                    try:
                        read_spec = s3_conn_spec_from_profile(prof, settings)
                    except ValueError as e:
                        context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(e))
                        raise RuntimeError("unreachable") from e
                    client = build_s3_client_from_spec(settings, read_spec)
                    bucket = read_spec.bucket
                    manifest_get_url = presign_get_object(
                        client, bucket=bucket, key=art.manifest_key, expires_in=ttl
                    )
                    reply = agent_pb2.RequestStorageGrantReply(
                        bundle_key=art.bundle_key,
                        manifest_key=art.manifest_key,
                        bundle_http_url=presign_get_object(
                            client, bucket=bucket, key=art.bundle_key, expires_in=ttl
                        ),
                        manifest_http_url=manifest_get_url,
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
        progress_audit: dict = {"agent_id": request.agent_id, "job_id": request.job_id}
        with grpc_governance(
            "ReportProgress",
            context,
            settings,
            audit_extra=progress_audit,
        ):
            auth_ctx = _authenticate_grpc(context, settings)
            try:
                agent_uuid = uuid.UUID(request.agent_id)
                job_uuid = uuid.UUID(request.job_id)
            except ValueError:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "invalid UUID")
                raise
            _require_agent_bearer_matches(auth_ctx, agent_uuid, context)

            db = SessionLocal()
            try:
                job = db.get(Job, job_uuid)
                if job is not None:
                    progress_audit["tenant_id"] = str(job.tenant_id)
                    _grpc_ensure_job_tenant(auth_ctx, job.tenant_id, context)
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
        complete_audit: dict = {"agent_id": request.agent_id, "job_id": request.job_id}
        with grpc_governance(
            "CompleteJob",
            context,
            settings,
            audit_extra=complete_audit,
        ):
            auth_ctx = _authenticate_grpc(context, settings)
            try:
                agent_uuid = uuid.UUID(request.agent_id)
                job_uuid = uuid.UUID(request.job_id)
            except ValueError:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "invalid UUID")
                raise
            _require_agent_bearer_matches(auth_ctx, agent_uuid, context)

            t_inner = time.monotonic()
            db = SessionLocal()
            try:
                job = db.get(Job, job_uuid)
                if job is None:
                    context.abort(grpc.StatusCode.NOT_FOUND, "job not found")
                    raise RuntimeError("unreachable")
                complete_audit["tenant_id"] = str(job.tenant_id)
                _grpc_ensure_job_tenant(auth_ctx, job.tenant_id, context)
                if job.lease_agent_id != agent_uuid:
                    context.abort(grpc.StatusCode.PERMISSION_DENIED, "job not leased to this agent")
                    raise RuntimeError("unreachable")

                job.completed_agent_hostname = _resolved_complete_agent_hostname(db, agent_uuid, request)

                if request.success:
                    if job.kind == JobKind.PATH_PRECHECK.value:
                        raw = (request.result_summary_json or "").strip()
                        if raw:
                            try:
                                parsed = json.loads(raw)
                                job.result_meta = parsed if isinstance(parsed, dict) else {"value": parsed}
                            except json.JSONDecodeError:
                                job.result_meta = {"parse_error": "invalid result_summary_json"}
                        job.status = JobStatus.SUCCESS.value
                        job.finished_at = datetime.now(timezone.utc)
                        JOB_TOTAL.labels(
                            *job_terminal_label_values(job, status="success", error_class="none"),
                        ).inc()
                    elif job.kind == JobKind.BACKUP.value:
                        tenant_row = db.get(Tenant, job.tenant_id)
                        try:
                            active_profile = require_active_profile(db)
                            storage = get_storage_for_profile(db, settings, active_profile.id)
                        except ValueError as e:
                            context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(e))
                            raise RuntimeError("unreachable") from e
                        bundle_key = request.bundle_key or ""
                        manifest_key = request.manifest_key or ""
                        if not bundle_key or not manifest_key:
                            BACKUP_INTEGRITY_CONTROL_REJECTS_TOTAL.labels(
                                reason="bundle_manifest_keys_missing",
                            ).inc()
                            context.abort(
                                grpc.StatusCode.INVALID_ARGUMENT,
                                "bundle/manifest keys required",
                            )
                        mpu_id = (request.bundle_multipart_upload_id or "").strip()
                        mpu_json = (request.bundle_multipart_parts_json or "").strip()
                        if mpu_id and mpu_json:
                            try:
                                parts_raw = json.loads(mpu_json)
                            except json.JSONDecodeError:
                                BACKUP_INTEGRITY_CONTROL_REJECTS_TOTAL.labels(
                                    reason="multipart_parts_json_invalid",
                                ).inc()
                                context.abort(
                                    grpc.StatusCode.INVALID_ARGUMENT,
                                    "invalid bundle_multipart_parts_json",
                                )
                                raise RuntimeError("unreachable")
                            if not isinstance(parts_raw, list) or not parts_raw:
                                BACKUP_INTEGRITY_CONTROL_REJECTS_TOTAL.labels(
                                    reason="multipart_parts_list_invalid",
                                ).inc()
                                context.abort(
                                    grpc.StatusCode.INVALID_ARGUMENT,
                                    "multipart parts list required",
                                )
                                raise RuntimeError("unreachable")
                            parts_sorted = sorted(
                                parts_raw,
                                key=lambda x: int(x.get("PartNumber", 0)),
                            )
                            parts_boto = [
                                {
                                    "PartNumber": int(p["PartNumber"]),
                                    "ETag": str(p["ETag"]),
                                }
                                for p in parts_sorted
                            ]
                            if not isinstance(storage, S3Storage):
                                context.abort(
                                    grpc.StatusCode.FAILED_PRECONDITION,
                                    "multipart completion requires s3 storage backend",
                                )
                                raise RuntimeError("unreachable")
                            s3c = storage.client
                            bucket_eff = storage.bucket
                            try:
                                s3c.complete_multipart_upload(
                                    Bucket=bucket_eff,
                                    Key=bundle_key,
                                    UploadId=mpu_id,
                                    MultipartUpload={"Parts": parts_boto},
                                )
                            except ClientError as e:
                                BACKUP_INTEGRITY_CONTROL_REJECTS_TOTAL.labels(
                                    reason="s3_complete_multipart_failed",
                                ).inc()
                                context.abort(
                                    grpc.StatusCode.FAILED_PRECONDITION,
                                    f"S3 complete_multipart_upload failed: {e}",
                                )
                                raise RuntimeError("unreachable") from e
                            if not storage.exists(bundle_key) or not storage.exists(manifest_key):
                                BACKUP_INTEGRITY_CONTROL_REJECTS_TOTAL.labels(
                                    reason="artifact_missing_post_multipart_complete",
                                ).inc()
                                context.abort(
                                    grpc.StatusCode.FAILED_PRECONDITION,
                                    "artifact objects missing after multipart complete",
                                )
                                raise RuntimeError("unreachable")
                        elif mpu_id or mpu_json:
                            BACKUP_INTEGRITY_CONTROL_REJECTS_TOTAL.labels(
                                reason="multipart_args_partial",
                            ).inc()
                            context.abort(
                                grpc.StatusCode.INVALID_ARGUMENT,
                                "bundle_multipart_upload_id and bundle_multipart_parts_json must both be set",
                            )
                            raise RuntimeError("unreachable")
                        elif not storage.exists(bundle_key) or not storage.exists(manifest_key):
                            BACKUP_INTEGRITY_CONTROL_REJECTS_TOTAL.labels(
                                reason="artifact_objects_missing",
                            ).inc()
                            context.abort(
                                grpc.StatusCode.FAILED_PRECONDITION,
                                "artifact objects missing",
                            )
                        try:
                            manifest_body = storage.get_bytes(manifest_key)
                            mf = json.loads(manifest_body.decode("utf-8"))
                        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
                            BACKUP_INTEGRITY_CONTROL_REJECTS_TOTAL.labels(
                                reason="manifest_read_failed",
                            ).inc()
                            context.abort(
                                grpc.StatusCode.FAILED_PRECONDITION,
                                f"cannot read manifest: {e}",
                            )
                            raise RuntimeError("unreachable") from e
                        if encryption_required(settings, tenant_row) and not manifest_declares_chunked_encryption(
                            mf
                        ):
                            BACKUP_INTEGRITY_CONTROL_REJECTS_TOTAL.labels(
                                reason="encryption_required_not_met",
                            ).inc()
                            context.abort(
                                grpc.StatusCode.FAILED_PRECONDITION,
                                "encrypted artifacts required by policy but manifest is not encrypted",
                            )
                            raise RuntimeError("unreachable")
                        mf_chk = str(mf.get("checksum_sha256") or "").lower()
                        req_chk = str(request.checksum_sha256 or "").lower()
                        if mf_chk and req_chk and mf_chk != req_chk:
                            BACKUP_INTEGRITY_CONTROL_REJECTS_TOTAL.labels(
                                reason="manifest_bundle_checksum_mismatch",
                            ).inc()
                            context.abort(
                                grpc.StatusCode.INVALID_ARGUMENT,
                                "bundle checksum does not match manifest",
                            )
                            raise RuntimeError("unreachable")
                        encrypted_flag = manifest_declares_chunked_encryption(mf)
                        if mpu_id and mpu_json and encrypted_flag:
                            MULTIPART_ENCRYPTED_MPU_COMPLETES_TOTAL.inc()
                        finished = datetime.now(timezone.utc)
                        retain_until = retain_until_from_backup_config(
                            job.config_snapshot or {},
                            at=finished,
                        )
                        art = Artifact(
                            tenant_id=job.tenant_id,
                            job_id=job.id,
                            storage_profile_id=active_profile.id,
                            storage_backend=storage.backend_name,
                            bundle_key=bundle_key,
                            manifest_key=manifest_key,
                            size_bytes=int(request.size_bytes),
                            checksum_sha256=request.checksum_sha256,
                            compression="tar.gz",
                            encrypted=encrypted_flag,
                            retain_until=retain_until,
                        )
                        db.add(art)
                        job.bundle_wip_multipart_upload_id = None
                        job.bundle_wip_content_length = None
                        job.bundle_wip_part_size_bytes = None
                        job.status = JobStatus.SUCCESS.value
                        job.finished_at = finished
                        JOB_TOTAL.labels(
                            *job_terminal_label_values(job, status="success", error_class="none"),
                        ).inc()
                        BILLING_COMMITTED_BYTES_TOTAL.labels(tenant_id=str(job.tenant_id)).inc(
                            max(0, int(request.size_bytes)),
                        )
                    elif job.kind == JobKind.RESTORE_DRILL.value:
                        job.status = JobStatus.SUCCESS.value
                        job.finished_at = datetime.now(timezone.utc)
                        raw = (request.result_summary_json or "").strip()
                        if raw:
                            try:
                                parsed = json.loads(raw)
                                job.result_meta = parsed if isinstance(parsed, dict) else {"value": parsed}
                            except json.JSONDecodeError:
                                job.result_meta = {"parse_error": "invalid result_summary_json"}
                        JOB_TOTAL.labels(
                            *job_terminal_label_values(job, status="success", error_class="none"),
                        ).inc()
                    else:
                        job.status = JobStatus.SUCCESS.value
                        job.finished_at = datetime.now(timezone.utc)
                        JOB_TOTAL.labels(
                            *job_terminal_label_values(job, status="success", error_class="none"),
                        ).inc()
                else:
                    if job.kind == JobKind.BACKUP.value:
                        ap = get_active_profile(db)
                        if ap is not None and ap.storage_type == "s3":
                            uid = job.bundle_wip_multipart_upload_id
                            if uid:
                                try:
                                    storage_abort = get_storage_for_active_profile(db, settings)
                                except ValueError:
                                    storage_abort = None
                                if isinstance(storage_abort, S3Storage):
                                    s3c = storage_abort.client
                                    bk, _mk = artifact_object_keys(settings, job.id, job.tenant_id)
                                    abort_multipart_upload_best_effort(
                                        s3c,
                                        bucket=storage_abort.bucket,
                                        key=bk,
                                        upload_id=uid,
                                    )
                    if job.kind == JobKind.PATH_PRECHECK.value:
                        raw = (request.result_summary_json or "").strip()
                        if raw:
                            try:
                                parsed = json.loads(raw)
                                job.result_meta = parsed if isinstance(parsed, dict) else {"value": parsed}
                            except json.JSONDecodeError:
                                job.result_meta = {"parse_error": "invalid result_summary_json"}
                    job.bundle_wip_multipart_upload_id = None
                    job.bundle_wip_content_length = None
                    job.bundle_wip_part_size_bytes = None
                    job.status = JobStatus.FAILED.value
                    job.error_code = (request.error_code or "FAILED")[:64]
                    job.error_message = (request.error_message or "")[:8000]
                    job.finished_at = datetime.now(timezone.utc)
                    ecls = agent_error_class(request.error_code)
                    JOB_TOTAL.labels(
                        *job_terminal_label_values(job, status="failed", error_class=ecls),
                    ).inc()

                job.lease_agent_id = None
                job.lease_agent_hostname = None
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
