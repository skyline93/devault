"""Compute artifact retention timestamps from file-plugin backup config."""

from __future__ import annotations

from datetime import datetime, timedelta


def retain_until_from_backup_config(cfg: dict | None, *, at: datetime) -> datetime | None:
    """Return UTC expiry instant from ``retention_days`` in policy/job config, or ``None`` for indefinite."""
    if not cfg:
        return None
    raw = cfg.get("retention_days")
    if raw is None:
        return None
    try:
        days = int(raw)
    except (TypeError, ValueError):
        return None
    if days < 1:
        return None
    return at + timedelta(days=days)
