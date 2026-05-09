"""Redis-backed per-Agent gRPC bearer tokens minted by Register."""

from __future__ import annotations

import json
from json import JSONDecodeError
import secrets
import uuid

from redis import Redis

SESSION_KEY_PREFIX = "devault:grpc:sess:"
VERSION_KEY_PREFIX = "devault:grpc:sess_ver:"


def mint_agent_session_token(
    redis_url: str,
    *,
    agent_id: uuid.UUID,
    ttl_seconds: int,
) -> tuple[str, int]:
    """Mint opaque Bearer secret bound to ``agent_id``. Returns ``(token, ttl_seconds)``."""
    r = Redis.from_url(redis_url, decode_responses=True)
    ver_key = f"{VERSION_KEY_PREFIX}{agent_id}"
    ver_raw = r.get(ver_key)
    ver = int(ver_raw) if ver_raw is not None else 0
    token = secrets.token_urlsafe(48)
    payload = json.dumps({"agent_id": str(agent_id), "v": ver})
    sess_key = f"{SESSION_KEY_PREFIX}{token}"
    r.setex(sess_key, ttl_seconds, payload)
    return token, ttl_seconds


def validate_and_refresh_agent_session(
    redis_url: str,
    raw_token: str,
    *,
    ttl_seconds: int,
) -> uuid.UUID | None:
    """Validate Bearer secret; bump TTL on success. ``None`` if invalid or revoked."""
    if not raw_token.strip():
        return None
    r = Redis.from_url(redis_url, decode_responses=True)
    sess_key = f"{SESSION_KEY_PREFIX}{raw_token.strip()}"
    raw = r.get(sess_key)
    if raw is None:
        return None
    try:
        data = json.loads(raw)
        aid = uuid.UUID(str(data["agent_id"]))
        v = int(data["v"])
    except (JSONDecodeError, ValueError, TypeError, KeyError):
        r.delete(sess_key)
        return None
    ver_key = f"{VERSION_KEY_PREFIX}{aid}"
    cur_raw = r.get(ver_key)
    cur = int(cur_raw) if cur_raw is not None else 0
    if v != cur:
        r.delete(sess_key)
        return None
    r.expire(sess_key, ttl_seconds)
    return aid


def revoke_all_grpc_sessions_for_agent(redis_url: str, agent_id: uuid.UUID) -> int:
    """Invalidate all session tokens for this agent. Returns new generation counter value."""
    r = Redis.from_url(redis_url, decode_responses=True)
    return int(r.incr(f"{VERSION_KEY_PREFIX}{agent_id}"))
