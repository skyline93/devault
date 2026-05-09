from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from prometheus_client.core import GaugeMetricFamily
from prometheus_client.registry import REGISTRY
from sqlalchemy import func, select

from devault.core.enums import JobStatus
from devault.db.models import Job
from devault.db.session import SessionLocal
from devault.settings import get_settings

logger = logging.getLogger(__name__)

_registered = False


class StuckJobsCollector:
    """Exposes counts of non-terminal jobs older than DEVAULT_JOB_STUCK_THRESHOLD_SECONDS."""

    def collect(self):
        mf = GaugeMetricFamily(
            "devault_jobs_overdue_nonterminal",
            "Jobs not in a terminal status whose coalesce(started_at, created_at) is older than "
            "DEVAULT_JOB_STUCK_THRESHOLD_SECONDS (stuck / SLA window signal)",
            labels=["stale_bucket"],
        )
        try:
            s = get_settings()
            cutoff = datetime.now(timezone.utc) - timedelta(seconds=s.job_stuck_threshold_seconds)
            active = (
                JobStatus.RUNNING.value,
                JobStatus.UPLOADING.value,
                JobStatus.VERIFYING.value,
            )
            with SessionLocal() as db:
                active_cnt = int(
                    db.execute(
                        select(func.count())
                        .select_from(Job)
                        .where(
                            Job.status.in_(active),
                            func.coalesce(Job.started_at, Job.created_at) < cutoff,
                        )
                    ).scalar_one()
                )
                pending_cnt = int(
                    db.execute(
                        select(func.count())
                        .select_from(Job)
                        .where(
                            Job.status == JobStatus.PENDING.value,
                            Job.created_at < cutoff,
                        )
                    ).scalar_one()
                )
            mf.add_metric(["active_work"], float(active_cnt))
            mf.add_metric(["pending_unleased"], float(pending_cnt))
        except Exception:
            logger.exception("stuck jobs collector query failed")
            mf.add_metric(["active_work"], 0.0)
            mf.add_metric(["pending_unleased"], 0.0)
        yield mf


def register_stuck_jobs_collector() -> None:
    global _registered
    if _registered:
        return
    REGISTRY.register(StuckJobsCollector())
    _registered = True
