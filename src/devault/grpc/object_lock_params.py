"""Derive S3 Object Lock parameters from file-plugin backup policy snapshot."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def object_lock_params_from_backup_cfg(
    cfg: dict | None,
    *,
    now: datetime | None = None,
) -> tuple[str | None, datetime | None]:
    """Return ``(ObjectLockMode, retain_until)`` when policy configures WORM retention."""
    if not cfg:
        return None, None
    mode = cfg.get("object_lock_mode")
    raw_days = cfg.get("object_lock_retain_days")
    if not mode or raw_days is None:
        return None, None
    if mode not in ("GOVERNANCE", "COMPLIANCE"):
        return None, None
    try:
        days = int(raw_days)
    except (TypeError, ValueError):
        return None, None
    if days < 1:
        return None, None
    t = now or datetime.now(timezone.utc)
    return str(mode), t + timedelta(days=days)
