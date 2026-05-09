from __future__ import annotations

from prometheus_client import Counter, Histogram

JOB_TOTAL = Counter(
    "devault_jobs_total",
    "Jobs finished by terminal status (success or failed)",
    ["kind", "plugin", "status", "tenant_id", "policy_id", "error_class"],
)


def _policy_metric_label(policy_id) -> str:
    return str(policy_id) if policy_id is not None else "none"


def agent_error_class(error_code: str | None) -> str:
    """Classify Agent-reported error_code for failed CompleteJob (bounded values for Prometheus)."""
    if not error_code:
        return "operational"
    u = error_code.strip().upper()
    if u in ("CHECKSUM_MISMATCH", "INVALID_MANIFEST"):
        return "integrity"
    return "operational"


def job_terminal_label_values(job, *, status: str, error_class: str = "none") -> tuple[str, ...]:
    return (
        job.kind,
        job.plugin,
        status,
        str(job.tenant_id),
        _policy_metric_label(job.policy_id),
        error_class,
    )


BACKUP_INTEGRITY_CONTROL_REJECTS_TOTAL = Counter(
    "devault_backup_integrity_control_rejects_total",
    "Backup CompleteJob rejected by control plane (pre-commit): manifest, checksum, or object checks",
    ["reason"],
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

MULTIPART_ENCRYPTED_MPU_COMPLETES_TOTAL = Counter(
    "devault_multipart_encrypted_mpu_completes_total",
    "Successful backup CompleteJob where bundle used S3 multipart and manifest carried encryption",
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
