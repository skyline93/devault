from __future__ import annotations

from datetime import datetime, timedelta, timezone

from devault.grpc.object_lock_params import object_lock_params_from_backup_cfg


def test_object_lock_params_from_backup_cfg() -> None:
    now = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    m, u = object_lock_params_from_backup_cfg(
        {"object_lock_mode": "GOVERNANCE", "object_lock_retain_days": 7},
        now=now,
    )
    assert m == "GOVERNANCE"
    assert u == now + timedelta(days=7)


def test_object_lock_params_incomplete_returns_none() -> None:
    assert object_lock_params_from_backup_cfg({"object_lock_mode": "GOVERNANCE"}) == (None, None)
    assert object_lock_params_from_backup_cfg({"object_lock_retain_days": 7}) == (None, None)
