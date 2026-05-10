from __future__ import annotations

import json
import uuid
from typing import Any

_CACHE_PREFIX_USER = "iam:perm:user"
_CACHE_PREFIX_API_KEY = "iam:perm:api_key"


def _redis(redis_url: str) -> Any | None:
    if not (redis_url or "").strip():
        return None
    try:
        import redis

        return redis.from_url(redis_url, decode_responses=True)
    except Exception:
        return None


def cache_key_user(tenant_id: uuid.UUID, user_id: uuid.UUID) -> str:
    return f"{_CACHE_PREFIX_USER}:{tenant_id}:{user_id}"


def cache_key_api_key(api_key_id: uuid.UUID) -> str:
    return f"{_CACHE_PREFIX_API_KEY}:{api_key_id}"


def get_cached_string_list(redis_url: str, key: str) -> list[str] | None:
    r = _redis(redis_url)
    if r is None:
        return None
    try:
        try:
            raw = r.get(key)
        except Exception:
            return None
        if raw is None:
            return None
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(x) for x in data]
        return None
    finally:
        try:
            r.close()
        except Exception:
            pass


def set_cached_string_list(redis_url: str, key: str, values: list[str], ttl_seconds: int) -> None:
    r = _redis(redis_url)
    if r is None:
        return
    try:
        try:
            r.setex(key, ttl_seconds, json.dumps(values))
        except Exception:
            return
    finally:
        try:
            r.close()
        except Exception:
            pass


def delete_cache_key(redis_url: str, key: str) -> None:
    r = _redis(redis_url)
    if r is None:
        return
    try:
        try:
            r.delete(key)
        except Exception:
            return
    finally:
        try:
            r.close()
        except Exception:
            pass


def invalidate_user_tenant(redis_url: str, tenant_id: uuid.UUID, user_id: uuid.UUID) -> None:
    delete_cache_key(redis_url, cache_key_user(tenant_id, user_id))


def invalidate_api_key(redis_url: str, api_key_id: uuid.UUID) -> None:
    delete_cache_key(redis_url, cache_key_api_key(api_key_id))
