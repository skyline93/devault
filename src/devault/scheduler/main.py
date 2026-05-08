"""Blocking scheduler process: reloads DB schedules periodically and creates pending backup jobs."""

from __future__ import annotations

import logging
import sys
import uuid
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from devault.core.enums import JobKind, JobStatus, JobTrigger, PluginName
from devault.db.models import Job, Policy, Schedule
from devault.db.session import SessionLocal

logger = logging.getLogger(__name__)


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
        for j in scheduler.get_jobs():
            if j.id.startswith("s_") and j.id not in keep:
                scheduler.remove_job(j.id)
                logger.info("Removed stale scheduler job %s", j.id)
    finally:
        db.close()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
    )
    scheduler = BlockingScheduler(timezone="UTC")
    sync_scheduler(scheduler)
    scheduler.add_job(
        lambda: sync_scheduler(scheduler),
        "interval",
        seconds=30,
        id="_reload_schedules",
        replace_existing=True,
    )
    logger.info("Scheduler started; reloading schedules every 30s")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    main()
