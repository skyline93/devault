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

MULTIPART_RESUME_GRANTS_TOTAL = Counter(
    "devault_multipart_resume_grants_total",
    "Storage grants that continued an in-flight multipart upload (ListParts + partial presigns)",
)

HTTP_REQUESTS_TOTAL = Counter(
    "devault_http_requests_total",
    "HTTP API requests (control plane)",
    ["method", "path_template"],
)

BILLING_COMMITTED_BYTES_TOTAL = Counter(
    "devault_billing_committed_backup_bytes_total",
    "Declared backup artifact bytes on successful CompleteJob (usage / chargeback signal)",
    ["tenant_id"],
)

RETENTION_PURGED_TOTAL = Counter(
    "devault_retention_artifacts_purged_total",
    "Artifacts removed by retention cleanup",
    ["tenant_id"],
)

RETENTION_PURGE_ERRORS_TOTAL = Counter(
    "devault_retention_purge_errors_total",
    "Failures during retention purge (storage delete or DB)",
)
