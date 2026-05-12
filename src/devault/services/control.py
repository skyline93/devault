from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from devault.api.cronutil import validate_cron_expression
from devault.api.schemas import (
    CreateBackupJobBody,
    CreatePathPrecheckJobBody,
    CreateRestoreDrillJobBody,
    CreateRestoreJobBody,
    FileBackupConfigV1,
    PolicyCreate,
    PolicyPatch,
    RestoreDrillScheduleCreate,
    RestoreDrillSchedulePatch,
    ScheduleCreate,
    SchedulePatch,
    TenantCreate,
    TenantPatch,
)
from devault.plugins.pgbackrest.config import PgbackrestPhysicalBackupConfigV1
from devault.core.enums import JobKind, JobStatus, JobTrigger, PluginName
from devault.core.locking import release_policy_job_lock
from devault.db.models import Artifact, Job, Policy, RestoreDrillSchedule, Schedule, Tenant
from devault.plugins.file.encryption_policy import encryption_required
from devault.services.policy_execution_binding import validate_bound_agent_for_policy
from devault.services.tenant_backup_allowlist import validate_policy_paths_against_tenant_allowlist
from devault.services.sso_policy import tenant_oidc_issuer_audience_in_use
from devault.settings import get_settings


def validate_backup_config_for_tenant(db: Session, tenant_id: uuid.UUID, cfg: FileBackupConfigV1) -> None:
    settings = get_settings()
    tenant = db.get(Tenant, tenant_id)
    if encryption_required(settings, tenant) and not cfg.encrypt_artifacts:
        raise HTTPException(
            400,
            detail="encrypt_artifacts is required for this tenant or global DEVAULT_REQUIRE_ENCRYPTED_ARTIFACTS",
        )


def create_tenant(db: Session, body: TenantCreate) -> Tenant:
    tid = body.id or uuid.uuid4()
    t = Tenant(id=tid, name=body.name.strip(), slug=body.slug)
    db.add(t)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="tenant slug already exists") from None
    db.refresh(t)
    return t


def patch_tenant(db: Session, tenant_id: uuid.UUID, body: TenantPatch) -> Tenant:
    t = db.get(Tenant, tenant_id)
    if t is None:
        raise HTTPException(404, detail="tenant not found")
    if body.name is not None:
        t.name = body.name.strip()
    if body.require_encrypted_artifacts is not None:
        t.require_encrypted_artifacts = body.require_encrypted_artifacts
    if body.kms_envelope_key_id is not None:
        t.kms_envelope_key_id = body.kms_envelope_key_id.strip() or None
    if body.s3_bucket is not None:
        t.s3_bucket = body.s3_bucket.strip() or None
    if body.s3_assume_role_arn is not None:
        t.s3_assume_role_arn = body.s3_assume_role_arn.strip() or None
    if body.s3_assume_role_external_id is not None:
        t.s3_assume_role_external_id = body.s3_assume_role_external_id.strip() or None
    if body.policy_paths_allowlist_mode is not None:
        t.policy_paths_allowlist_mode = body.policy_paths_allowlist_mode
    if body.require_mfa_for_admins is not None:
        t.require_mfa_for_admins = body.require_mfa_for_admins
    next_oidc_iss = t.sso_oidc_issuer
    next_oidc_aud = t.sso_oidc_audience
    if body.sso_oidc_issuer is not None:
        raw_iss = body.sso_oidc_issuer.strip() or None
        next_oidc_iss = raw_iss.rstrip("/") if raw_iss else None
    if body.sso_oidc_audience is not None:
        next_oidc_aud = body.sso_oidc_audience.strip() or None
    if (next_oidc_iss is None) != (next_oidc_aud is None):
        raise HTTPException(
            status_code=400,
            detail="sso_oidc_issuer and sso_oidc_audience must both be set or both cleared",
        )
    if next_oidc_iss and next_oidc_aud:
        if tenant_oidc_issuer_audience_in_use(
            db,
            issuer=next_oidc_iss,
            audience=next_oidc_aud,
            exclude_tenant_id=t.id,
        ):
            raise HTTPException(
                status_code=409,
                detail="OIDC issuer and audience are already configured on another tenant",
            )
    t.sso_oidc_issuer = next_oidc_iss
    t.sso_oidc_audience = next_oidc_aud
    if body.sso_oidc_role_claim is not None:
        t.sso_oidc_role_claim = body.sso_oidc_role_claim.strip() or "devault_role"
    if body.sso_oidc_email_claim is not None:
        t.sso_oidc_email_claim = body.sso_oidc_email_claim.strip() or "email"
    if body.sso_password_login_disabled is not None:
        t.sso_password_login_disabled = body.sso_password_login_disabled
    if body.sso_jit_provisioning is not None:
        t.sso_jit_provisioning = body.sso_jit_provisioning
    if body.sso_saml_entity_id is not None:
        t.sso_saml_entity_id = body.sso_saml_entity_id.strip() or None
    if body.sso_saml_acs_url is not None:
        t.sso_saml_acs_url = body.sso_saml_acs_url.strip() or None

    db.commit()
    db.refresh(t)
    return t


def create_policy(db: Session, body: PolicyCreate, *, tenant_id: uuid.UUID) -> Policy:
    if body.plugin not in (PluginName.FILE.value, PluginName.POSTGRES_PGBACKREST.value):
        raise HTTPException(400, detail="Unsupported policy plugin")
    if body.plugin == PluginName.FILE.value:
        raw = dict(body.config)
        if "version" not in raw:
            raw["version"] = 1
        file_cfg = FileBackupConfigV1.model_validate(raw)
        validate_backup_config_for_tenant(db, tenant_id, file_cfg)
        validate_policy_paths_against_tenant_allowlist(db, tenant_id, file_cfg.paths)
        config_json = file_cfg.model_dump(mode="json")
    else:
        pg_cfg = PgbackrestPhysicalBackupConfigV1.model_validate(body.config)
        config_json = pg_cfg.model_dump(mode="json")
    validate_bound_agent_for_policy(
        db,
        tenant_id=tenant_id,
        bound_agent_id=body.bound_agent_id,
    )
    p = Policy(
        tenant_id=tenant_id,
        name=body.name,
        plugin=body.plugin,
        config=config_json,
        enabled=body.enabled,
        bound_agent_id=body.bound_agent_id,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def patch_policy(db: Session, policy_id: uuid.UUID, body: PolicyPatch, *, tenant_id: uuid.UUID) -> Policy:
    p = db.get(Policy, policy_id)
    if p is None or p.tenant_id != tenant_id:
        raise HTTPException(404, detail="policy not found")
    if body.name is not None:
        p.name = body.name
    if body.config is not None:
        if p.plugin == PluginName.FILE.value:
            raw = dict(body.config)
            if "version" not in raw:
                raw["version"] = 1
            file_cfg = FileBackupConfigV1.model_validate(raw)
            validate_backup_config_for_tenant(db, tenant_id, file_cfg)
            validate_policy_paths_against_tenant_allowlist(db, tenant_id, file_cfg.paths)
            p.config = file_cfg.model_dump(mode="json")
        elif p.plugin == PluginName.POSTGRES_PGBACKREST.value:
            pg_cfg = PgbackrestPhysicalBackupConfigV1.model_validate(body.config)
            p.config = pg_cfg.model_dump(mode="json")
        else:
            raise HTTPException(400, detail="Unsupported policy plugin")
    if body.enabled is not None:
        p.enabled = body.enabled
    upd = body.model_dump(exclude_unset=True)
    if "bound_agent_id" in upd:
        ba = upd["bound_agent_id"]
        if ba is None:
            raise HTTPException(400, detail="bound_agent_id is required")
        validate_bound_agent_for_policy(
            db,
            tenant_id=tenant_id,
            bound_agent_id=ba,
        )
        p.bound_agent_id = ba
    p.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(p)
    return p


def patch_artifact_legal_hold(
    db: Session,
    artifact_id: uuid.UUID,
    *,
    tenant_id: uuid.UUID,
    legal_hold: bool,
) -> Artifact:
    art = db.get(Artifact, artifact_id)
    if art is None or art.tenant_id != tenant_id:
        raise HTTPException(404, detail="artifact not found")
    art.legal_hold = legal_hold
    db.commit()
    db.refresh(art)
    return art


def delete_policy(db: Session, policy_id: uuid.UUID, *, tenant_id: uuid.UUID) -> None:
    p = db.get(Policy, policy_id)
    if p is None or p.tenant_id != tenant_id:
        raise HTTPException(404, detail="policy not found")
    db.delete(p)
    db.commit()


def create_schedule(db: Session, body: ScheduleCreate, *, tenant_id: uuid.UUID) -> Schedule:
    pol = db.get(Policy, body.policy_id)
    if pol is None or pol.tenant_id != tenant_id:
        raise HTTPException(404, detail="policy not found")
    validate_cron_expression(body.cron_expression)
    s = Schedule(
        tenant_id=pol.tenant_id,
        policy_id=body.policy_id,
        cron_expression=body.cron_expression.strip(),
        timezone=body.timezone,
        enabled=body.enabled,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def patch_schedule(db: Session, schedule_id: uuid.UUID, body: SchedulePatch, *, tenant_id: uuid.UUID) -> Schedule:
    s = db.get(Schedule, schedule_id)
    if s is None or s.tenant_id != tenant_id:
        raise HTTPException(404, detail="schedule not found")
    if body.cron_expression is not None:
        validate_cron_expression(body.cron_expression)
        s.cron_expression = body.cron_expression.strip()
    if body.timezone is not None:
        s.timezone = body.timezone
    if body.enabled is not None:
        s.enabled = body.enabled
    db.commit()
    db.refresh(s)
    return s


def delete_schedule(db: Session, schedule_id: uuid.UUID, *, tenant_id: uuid.UUID) -> None:
    s = db.get(Schedule, schedule_id)
    if s is None or s.tenant_id != tenant_id:
        raise HTTPException(404, detail="schedule not found")
    db.delete(s)
    db.commit()


def create_backup_job(db: Session, body: CreateBackupJobBody, *, tenant_id: uuid.UUID) -> Job:
    policy_id: uuid.UUID | None = None
    plugin: str
    snap: dict

    if body.policy_id is not None:
        pol = db.get(Policy, body.policy_id)
        if pol is None or pol.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail="policy not found")
        if not pol.enabled:
            raise HTTPException(status_code=400, detail="policy is disabled")
        if pol.plugin not in (PluginName.FILE.value, PluginName.POSTGRES_PGBACKREST.value):
            raise HTTPException(status_code=400, detail="Unsupported policy plugin")
        if body.plugin is not None and body.plugin != pol.plugin:
            raise HTTPException(status_code=400, detail="plugin does not match policy")
        plugin = pol.plugin
        snap = dict(pol.config)
        policy_id = pol.id
        if plugin == PluginName.FILE.value:
            raw = dict(snap)
            if "version" not in raw:
                raw["version"] = 1
            validate_backup_config_for_tenant(db, tenant_id, FileBackupConfigV1.model_validate(raw))
    else:
        assert body.config is not None
        if body.plugin is None:
            raise HTTPException(status_code=400, detail="plugin is required for inline backup config")
        plugin = body.plugin
        if plugin == PluginName.FILE.value:
            raw = dict(body.config)
            if "version" not in raw:
                raw["version"] = 1
            file_cfg = FileBackupConfigV1.model_validate(raw)
            validate_backup_config_for_tenant(db, tenant_id, file_cfg)
            snap = file_cfg.model_dump(mode="json")
        else:
            pg_cfg = PgbackrestPhysicalBackupConfigV1.model_validate(body.config)
            snap = pg_cfg.model_dump(mode="json")

    job = Job(
        tenant_id=tenant_id,
        kind=JobKind.BACKUP.value,
        plugin=plugin,
        status=JobStatus.PENDING.value,
        trigger=JobTrigger.MANUAL.value,
        idempotency_key=body.idempotency_key,
        config_snapshot=snap,
        policy_id=policy_id,
    )
    db.add(job)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if body.idempotency_key:
            existing = db.scalar(
                select(Job).where(
                    Job.tenant_id == tenant_id,
                    Job.idempotency_key == body.idempotency_key,
                )
            )
            if existing is not None:
                return existing
        raise
    db.refresh(job)
    return job


def create_path_precheck_job(db: Session, body: CreatePathPrecheckJobBody, *, tenant_id: uuid.UUID) -> Job:
    """Enqueue a read-only Agent job that checks policy backup paths exist and are readable."""
    pol = db.get(Policy, body.policy_id)
    if pol is None or pol.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="policy not found")
    if not pol.enabled:
        raise HTTPException(status_code=400, detail="policy is disabled")
    if pol.plugin != PluginName.FILE.value:
        raise HTTPException(status_code=400, detail="only file policy supported")
    raw_cfg = dict(pol.config or {})
    if "version" not in raw_cfg:
        raw_cfg["version"] = 1
    cfg = FileBackupConfigV1.model_validate(raw_cfg)
    snap = {
        "version": 1,
        "path_precheck": True,
        "paths": [str(p) for p in cfg.paths],
        "tenant_id": str(tenant_id),
    }
    job = Job(
        tenant_id=tenant_id,
        kind=JobKind.PATH_PRECHECK.value,
        plugin=PluginName.FILE.value,
        status=JobStatus.PENDING.value,
        trigger=JobTrigger.MANUAL.value,
        config_snapshot=snap,
        policy_id=pol.id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def create_restore_drill_job(db: Session, body: CreateRestoreDrillJobBody, *, tenant_id: uuid.UUID) -> Job:
    art = db.get(Artifact, body.artifact_id)
    if art is None or art.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="artifact not found")

    base = Path(body.drill_base_path)
    if not base.is_absolute():
        raise HTTPException(status_code=400, detail="drill_base_path must be absolute")
    base = base.resolve(strict=False)

    cfg = {
        "version": 1,
        "artifact_id": str(body.artifact_id),
        "drill_base_path": str(base),
        "restore_drill": True,
    }
    job = Job(
        tenant_id=tenant_id,
        kind=JobKind.RESTORE_DRILL.value,
        plugin=PluginName.FILE.value,
        status=JobStatus.PENDING.value,
        trigger=JobTrigger.MANUAL.value,
        config_snapshot=cfg,
        restore_artifact_id=body.artifact_id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def create_restore_job(db: Session, body: CreateRestoreJobBody, *, tenant_id: uuid.UUID) -> Job:
    art = db.get(Artifact, body.artifact_id)
    if art is None or art.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="artifact not found")

    target = Path(body.target_path)
    if not target.is_absolute():
        raise HTTPException(status_code=400, detail="target_path must be absolute")
    target = target.resolve(strict=False)
    if target.exists() and any(target.iterdir()) and not body.confirm_overwrite_non_empty:
        raise HTTPException(
            status_code=400,
            detail="target_path is not empty; set confirm_overwrite_non_empty=true to proceed",
        )

    cfg = {
        "version": 1,
        "artifact_id": str(body.artifact_id),
        "target_path": str(target),
        "confirm_overwrite_non_empty": body.confirm_overwrite_non_empty,
    }
    job = Job(
        tenant_id=tenant_id,
        kind=JobKind.RESTORE.value,
        plugin=PluginName.FILE.value,
        status=JobStatus.PENDING.value,
        trigger=JobTrigger.MANUAL.value,
        config_snapshot=cfg,
        restore_artifact_id=body.artifact_id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def cancel_job(db: Session, job_id: uuid.UUID, *, tenant_id: uuid.UUID) -> Job:
    job = db.get(Job, job_id)
    if job is None or job.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="job not found")
    terminal = {
        JobStatus.SUCCESS.value,
        JobStatus.FAILED.value,
        JobStatus.CANCELLED.value,
    }
    if job.status in terminal:
        raise HTTPException(status_code=400, detail="job already finished")
    settings = get_settings()
    if job.policy_id and job.status in (
        JobStatus.RUNNING.value,
        JobStatus.UPLOADING.value,
        JobStatus.VERIFYING.value,
    ):
        release_policy_job_lock(
            job.policy_id,
            job.id,
            redis_url=settings.redis_url,
        )
    job.lease_agent_id = None
    job.lease_agent_hostname = None
    job.lease_expires_at = None
    job.status = JobStatus.CANCELLED.value
    job.error_code = "CANCELLED"
    job.error_message = "Cancelled by user"
    job.finished_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)
    return job


def create_restore_drill_schedule(
    db: Session, body: RestoreDrillScheduleCreate, *, tenant_id: uuid.UUID
) -> RestoreDrillSchedule:
    art = db.get(Artifact, body.artifact_id)
    if art is None or art.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="artifact not found")
    validate_cron_expression(body.cron_expression)
    base = Path(body.drill_base_path)
    if not base.is_absolute():
        raise HTTPException(status_code=400, detail="drill_base_path must be absolute")
    sch = RestoreDrillSchedule(
        tenant_id=tenant_id,
        artifact_id=body.artifact_id,
        cron_expression=body.cron_expression.strip(),
        timezone=body.timezone,
        enabled=body.enabled,
        drill_base_path=str(base.resolve(strict=False)),
    )
    db.add(sch)
    db.commit()
    db.refresh(sch)
    return sch


def patch_restore_drill_schedule(
    db: Session,
    schedule_id: uuid.UUID,
    body: RestoreDrillSchedulePatch,
    *,
    tenant_id: uuid.UUID,
) -> RestoreDrillSchedule:
    s = db.get(RestoreDrillSchedule, schedule_id)
    if s is None or s.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="restore drill schedule not found")
    if body.artifact_id is not None:
        art = db.get(Artifact, body.artifact_id)
        if art is None or art.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail="artifact not found")
        s.artifact_id = body.artifact_id
    if body.cron_expression is not None:
        validate_cron_expression(body.cron_expression)
        s.cron_expression = body.cron_expression.strip()
    if body.timezone is not None:
        s.timezone = body.timezone
    if body.enabled is not None:
        s.enabled = body.enabled
    if body.drill_base_path is not None:
        bp = Path(body.drill_base_path)
        if not bp.is_absolute():
            raise HTTPException(status_code=400, detail="drill_base_path must be absolute")
        s.drill_base_path = str(bp.resolve(strict=False))
    db.commit()
    db.refresh(s)
    return s


def delete_restore_drill_schedule(db: Session, schedule_id: uuid.UUID, *, tenant_id: uuid.UUID) -> None:
    s = db.get(RestoreDrillSchedule, schedule_id)
    if s is None or s.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="restore drill schedule not found")
    db.delete(s)
    db.commit()


def retry_failed_backup_job(db: Session, job_id: uuid.UUID, *, tenant_id: uuid.UUID) -> Job:
    job = db.get(Job, job_id)
    if job is None or job.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="job not found")
    if job.status != JobStatus.FAILED.value:
        raise HTTPException(status_code=400, detail="only failed jobs can be retried")
    if job.kind != JobKind.BACKUP.value:
        raise HTTPException(status_code=400, detail="only backup jobs can be retried")

    new_job = Job(
        tenant_id=job.tenant_id,
        kind=JobKind.BACKUP.value,
        plugin=job.plugin,
        status=JobStatus.PENDING.value,
        trigger=JobTrigger.RETRY.value,
        policy_id=job.policy_id,
        config_snapshot=dict(job.config_snapshot),
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    return new_job
