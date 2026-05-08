from __future__ import annotations

from datetime import datetime, timezone

from croniter import CroniterBadCronError, croniter
from fastapi import HTTPException


def validate_cron_expression(expr: str) -> None:
    try:
        croniter(expr, datetime.now(timezone.utc))
    except (CroniterBadCronError, KeyError, ValueError) as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid cron expression: {e}",
        ) from e
