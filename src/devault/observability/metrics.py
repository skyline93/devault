from __future__ import annotations

from prometheus_client import Counter, Histogram

JOB_TOTAL = Counter(
    "devault_jobs_total",
    "Jobs finished by terminal status",
    ["kind", "plugin", "status"],
)

JOB_DURATION_SECONDS = Histogram(
    "devault_job_duration_seconds",
    "Wall time for job execution in worker",
    ["kind", "plugin"],
    buckets=(0.5, 1, 5, 10, 30, 60, 120, 300, 600, float("inf")),
)

POLICY_LOCK_CONTENTION = Counter(
    "devault_policy_lock_contention_total",
    "Backup skipped or failed due to policy lock",
    ["plugin"],
)
