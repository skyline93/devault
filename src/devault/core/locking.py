from __future__ import annotations

import uuid

from redis import Redis


def policy_backup_lock_key(policy_id: uuid.UUID) -> str:
    return f"devault:policy-lock:{policy_id}"


def try_acquire_policy_job_lock(
    policy_id: uuid.UUID,
    job_id: uuid.UUID,
    *,
    redis_url: str,
    ttl_sec: int = 7200,
) -> bool:
    """Exclusive policy lock: one in-flight backup per policy. Value = job_id for safe release."""
    r = Redis.from_url(redis_url, decode_responses=True)
    key = policy_backup_lock_key(policy_id)
    return bool(r.set(key, str(job_id), nx=True, ex=ttl_sec))


def release_policy_job_lock(
    policy_id: uuid.UUID,
    job_id: uuid.UUID,
    *,
    redis_url: str,
) -> None:
    r = Redis.from_url(redis_url, decode_responses=True)
    key = policy_backup_lock_key(policy_id)
    cur = r.get(key)
    if cur == str(job_id):
        r.delete(key)
