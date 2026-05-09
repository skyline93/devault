"""Blocking scheduler process: reloads DB schedules periodically and creates pending backup jobs."""

from __future__ import annotations

import logging
import sys
import uuid
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from devault.core.enums import JobKind, JobStatus, JobTrigger
from devault.db.models import Artifact, Job, Policy, RestoreDrillSchedule, Schedule
from devault.db.session import SessionLocal
from devault.services.retention import purge_expired_artifacts
from devault.settings import get_settings

logger = logging.getLogger(__name__)


def fire_scheduled_restore_drill(schedule_id: str) -> None:
    """Enqueue a restore_drill job from a RestoreDrillSchedule row."""
    sid = uuid.UUID(schedule_id)
    db = SessionLocal()
    try:
        sch = db.get(RestoreDrillSchedule, sid)
        if sch is None or not sch.enabled:
            logger.warning("RestoreDrillSchedule %s missing or disabled, skip", schedule_id)
            return
        art = db.get(Artifact, sch.artifact_id)
        if art is None or art.tenant_id != sch.tenant_id:
            logger.warning(
                "Artifact %s missing or tenant mismatch for restore drill schedule %s, skip",
                sch.artifact_id,
                schedule_id,
            )
            return

        cfg = {
            "version": 1,
            "artifact_id": str(art.id),
            "drill_base_path": sch.drill_base_path,
            "restore_drill": True,
            "restore_drill_schedule_id": str(sch.id),
        }
        job = Job(
            tenant_id=sch.tenant_id,
            kind=JobKind.RESTORE_DRILL.value,
            plugin="file",
            status=JobStatus.PENDING.value,
            trigger=JobTrigger.SCHEDULED.value,
            config_snapshot=cfg,
            restore_artifact_id=art.id,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        logger.info(
            "Scheduled restore drill enqueued job_id=%s schedule_id=%s artifact_id=%s",
            job.id,
            schedule_id,
            art.id,
        )
    finally:
        db.close()


def fire_scheduled_backup(schedule_id: str) -> None:
    """Create a pending backup job from schedule + policy (claimed by an Agent via gRPC)."""
    sid = uuid.UUID(schedule_id)
    db = SessionLocal()
    try:
        sch = db.get(Schedule, sid)
        if sch is None or not sch.enabled:
            logger.warning("Schedule %s missing or disabled, skip", schedule_id)
            return
        policy = db.get(Policy, sch.policy_id)
        if policy is None or not policy.enabled:
            logger.warning("Policy %s missing or disabled, skip", sch.policy_id)
            return

        job = Job(
            tenant_id=policy.tenant_id,
            kind=JobKind.BACKUP.value,
            plugin=policy.plugin,
            status=JobStatus.PENDING.value,
            trigger=JobTrigger.SCHEDULED.value,
            policy_id=policy.id,
            config_snapshot=dict(policy.config),
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        logger.info(
            "Scheduled backup enqueued job_id=%s schedule_id=%s policy_id=%s",
            job.id,
            schedule_id,
            policy.id,
        )
    finally:
        db.close()


def sync_scheduler(scheduler: BlockingScheduler) -> None:
    db = SessionLocal()
    keep: set[str] = set()
    try:
        rows = db.scalars(select(Schedule).where(Schedule.enabled.is_(True))).all()
        for sch in rows:
            pol = db.get(Policy, sch.policy_id)
            if pol is None or not pol.enabled:
                continue
            jid = f"s_{sch.id}"
            keep.add(jid)
            try:
                tz = ZoneInfo(sch.timezone)
            except ZoneInfoNotFoundError:
                logger.warning("Unknown timezone %r for schedule %s, using UTC", sch.timezone, sch.id)
                tz = ZoneInfo("UTC")
            trigger = CronTrigger.from_crontab(sch.cron_expression.strip(), timezone=tz)
            scheduler.add_job(
                fire_scheduled_backup,
                trigger,
                args=[str(sch.id)],
                id=jid,
                replace_existing=True,
                max_instances=1,
                coalesce=True,
            )
        rd_rows = db.scalars(
            select(RestoreDrillSchedule).where(RestoreDrillSchedule.enabled.is_(True))
        ).all()
        for sch in rd_rows:
            art = db.get(Artifact, sch.artifact_id)
            if art is None or art.tenant_id != sch.tenant_id:
                continue
            jid = f"rd_{sch.id}"
            keep.add(jid)
            try:
                tz = ZoneInfo(sch.timezone)
            except ZoneInfoNotFoundError:
                logger.warning(
                    "Unknown timezone %r for restore drill schedule %s, using UTC",
                    sch.timezone,
                    sch.id,
                )
                tz = ZoneInfo("UTC")
            trigger = CronTrigger.from_crontab(sch.cron_expression.strip(), timezone=tz)
            scheduler.add_job(
                fire_scheduled_restore_drill,
                trigger,
                args=[str(sch.id)],
                id=jid,
                replace_existing=True,
                max_instances=1,
                coalesce=True,
            )
        for j in scheduler.get_jobs():
            jid = getattr(j, "id", "")
            if (
                isinstance(jid, str)
                and (jid.startswith("s_") or jid.startswith("rd_"))
                and jid not in keep
            ):
                scheduler.remove_job(jid)
                logger.info("Removed stale scheduler job %s", jid)
    finally:
        db.close()


def run_retention_purge() -> None:
    settings = get_settings()
    n, err = purge_expired_artifacts(settings)
    if n or err:
        logger.info("retention purge purged=%s errors=%s", n, err)


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] in ("--version", "-V"):
        from devault import __version__

        print(__version__)
        return
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
    )
    scheduler = BlockingScheduler(timezone="UTC")
    sync_scheduler(scheduler)
    s0 = get_settings()
    scheduler.add_job(
        lambda: sync_scheduler(scheduler),
        "interval",
        seconds=30,
        id="_reload_schedules",
        replace_existing=True,
    )
    interval = max(60, int(s0.retention_cleanup_interval_seconds))
    scheduler.add_job(
        run_retention_purge,
        "interval",
        seconds=interval,
        id="_retention_purge",
        replace_existing=True,
    )
    logger.info(
        "Scheduler started; reloading schedules every 30s; retention purge every %ss (enabled=%s)",
        interval,
        s0.retention_cleanup_enabled,
    )
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    main()
