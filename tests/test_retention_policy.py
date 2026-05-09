from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from devault.retention.policy import retain_until_from_backup_config


def test_retain_until_none_without_config() -> None:
    at = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
    assert retain_until_from_backup_config({}, at=at) is None
    assert retain_until_from_backup_config(None, at=at) is None


def test_retain_until_none_when_omitted() -> None:
    at = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
    assert retain_until_from_backup_config({"version": 1}, at=at) is None


def test_retain_until_adds_days() -> None:
    at = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
    ru = retain_until_from_backup_config({"retention_days": 7}, at=at)
    assert ru == at + timedelta(days=7)


@pytest.mark.parametrize(
    "cfg",
    [
        {"retention_days": 0},
        {"retention_days": -1},
        {"retention_days": "x"},
    ],
)
def test_retain_until_invalid_days(cfg: dict) -> None:
    at = datetime(2026, 5, 1, tzinfo=timezone.utc)
    assert retain_until_from_backup_config(cfg, at=at) is None
