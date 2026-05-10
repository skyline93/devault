from __future__ import annotations

from fastapi import HTTPException, status
from redis import Redis


def check_sliding_rate_limit(
    redis_url: str,
    client_ip: str,
    *,
    max_per_minute: int,
    key_prefix: str,
) -> None:
    if max_per_minute <= 0:
        return
    key = f"{key_prefix}:{client_ip}"
    r = Redis.from_url(redis_url, decode_responses=True)
    n = r.incr(key)
    if n == 1:
        r.expire(key, 60)
    if n > max_per_minute:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="rate limit exceeded; retry later",
        )
