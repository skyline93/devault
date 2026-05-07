from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from devault.core.enums import JobKind, JobStatus, PluginName
from devault.db.models import Artifact, Job
from devault.db.session import SessionLocal
from devault.plugins.file import FileBackupError, run_file_backup, run_file_restore
from devault.settings import get_settings
from devault.storage import get_storage
from devault.worker.app import celery_app

logger = logging.getLogger(__name__)


def _fail_job(db, job: Job, code: str, message: str) -> None:
    job.status = JobStatus.FAILED.value
    job.error_code = code
    job.error_message = message[:8000]
    job.finished_at = datetime.now(timezone.utc)
    db.commit()


@celery_app.task(name="devault.run_backup_job", bind=True)
def run_backup_job(self, job_id: str) -> None:
    settings = get_settings()
    storage = get_storage(settings)
    jid = uuid.UUID(job_id)
    db = SessionLocal()
    try:
        job = db.get(Job, jid)
        if job is None:
            logger.error("Job %s not found", job_id)
            return
        if job.plugin != PluginName.FILE.value:
            _fail_job(db, job, "UNSUPPORTED_PLUGIN", f"Plugin {job.plugin} not supported")
            return
        if job.kind != JobKind.BACKUP.value:
            _fail_job(db, job, "INVALID_KIND", "Not a backup job")
            return

        job.status = JobStatus.RUNNING.value
        job.started_at = datetime.now(timezone.utc)
        db.commit()

        try:
            job.status = JobStatus.UPLOADING.value
            db.commit()
            outcome = run_file_backup(job=job, settings=settings, storage=storage)
            job.status = JobStatus.VERIFYING.value
            db.commit()

            art = Artifact(
                job_id=job.id,
                storage_backend=storage.backend_name,
                bundle_key=outcome.bundle_key,
                manifest_key=outcome.manifest_key,
                size_bytes=outcome.size_bytes,
                checksum_sha256=outcome.checksum_sha256,
                compression="tar.gz",
                encrypted=False,
            )
            db.add(art)
            job.status = JobStatus.SUCCESS.value
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
        except FileBackupError as e:
            logger.warning("Backup failed job=%s code=%s msg=%s", job_id, e.code, e.message)
            _fail_job(db, job, e.code, e.message)
        except Exception as e:
            logger.exception("Backup crashed job=%s", job_id)
            _fail_job(db, job, "INTERNAL_ERROR", f"{type(e).__name__}: {e}")
    finally:
        db.close()


@celery_app.task(name="devault.run_restore_job", bind=True)
def run_restore_job(self, job_id: str) -> None:
    settings = get_settings()
    storage = get_storage(settings)
    jid = uuid.UUID(job_id)
    db = SessionLocal()
    try:
        job = db.get(Job, jid)
        if job is None:
            logger.error("Job %s not found", job_id)
            return
        if job.plugin != PluginName.FILE.value:
            _fail_job(db, job, "UNSUPPORTED_PLUGIN", f"Plugin {job.plugin} not supported")
            return
        if job.kind != JobKind.RESTORE.value:
            _fail_job(db, job, "INVALID_KIND", "Not a restore job")
            return

        job.status = JobStatus.RUNNING.value
        job.started_at = datetime.now(timezone.utc)
        db.commit()

        try:
            run_file_restore(db=db, job=job, settings=settings, storage=storage)
            job.status = JobStatus.SUCCESS.value
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
        except FileBackupError as e:
            logger.warning("Restore failed job=%s code=%s msg=%s", job_id, e.code, e.message)
            _fail_job(db, job, e.code, e.message)
        except Exception as e:
            logger.exception("Restore crashed job=%s", job_id)
            _fail_job(db, job, "INTERNAL_ERROR", f"{type(e).__name__}: {e}")
    finally:
        db.close()
