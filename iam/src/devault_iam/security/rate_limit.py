from __future__ import annotations


def check_sliding_rate_limit(
    redis_url: str,
    client_ip: str,
    *,
    max_per_minute: int,
    key_prefix: str,
) -> None:
    """Raise PermissionError if rate limit exceeded. No-op if redis_url empty or limit disabled."""
    if not redis_url.strip() or max_per_minute <= 0:
        return
    import redis

    try:
        r = redis.from_url(redis_url, decode_responses=True)
        key = f"{key_prefix}:{client_ip}"
        try:
            n = int(r.incr(key))
            if n == 1:
                r.expire(key, 60)
            if n > max_per_minute:
                raise PermissionError("rate_limited")
        finally:
            try:
                r.close()
            except Exception:
                pass
    except PermissionError:
        raise
    except Exception:
        return


def check_sliding_login_rate_limit(
    redis_url: str,
    client_ip: str,
    *,
    max_per_minute: int,
    key_prefix: str = "devault_iam:login_rl",
) -> None:
    """Raise PermissionError if login rate limit exceeded."""
    check_sliding_rate_limit(
        redis_url,
        client_ip,
        max_per_minute=max_per_minute,
        key_prefix=key_prefix,
    )
