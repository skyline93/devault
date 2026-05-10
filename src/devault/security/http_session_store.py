from __future__ import annotations

import json
import secrets
import uuid
from dataclasses import dataclass
from typing import Any

from redis import Redis

SESSION_REDIS_PREFIX = "devault:http_session:"


@dataclass(frozen=True, slots=True)
class HttpSessionPayload:
    user_id: uuid.UUID
    mfa_verified: bool = True

    @classmethod
    def from_json(cls, raw: str) -> HttpSessionPayload | None:
        try:
            d: dict[str, Any] = json.loads(raw)
            uid = d.get("user_id")
            if not uid:
                return None
            mv = d.get("mfa_verified", True)
            return cls(user_id=uuid.UUID(str(uid)), mfa_verified=bool(mv))
        except (json.JSONDecodeError, ValueError, TypeError):
            return None

    def to_json(self) -> str:
        return json.dumps({"user_id": str(self.user_id), "mfa_verified": self.mfa_verified})


def new_session_id() -> str:
    return secrets.token_urlsafe(32)


def redis_session_key(session_id: str) -> str:
    return f"{SESSION_REDIS_PREFIX}{session_id}"


def save_session(redis_url: str, session_id: str, payload: HttpSessionPayload, ttl_seconds: int) -> None:
    r = Redis.from_url(redis_url, decode_responses=True)
    r.set(redis_session_key(session_id), payload.to_json(), ex=int(ttl_seconds))


def load_session(redis_url: str, session_id: str) -> HttpSessionPayload | None:
    r = Redis.from_url(redis_url, decode_responses=True)
    raw = r.get(redis_session_key(session_id))
    if not raw:
        return None
    return HttpSessionPayload.from_json(str(raw))


def delete_session(redis_url: str, session_id: str) -> None:
    r = Redis.from_url(redis_url, decode_responses=True)
    r.delete(redis_session_key(session_id))


def touch_session_ttl(redis_url: str, session_id: str, ttl_seconds: int) -> bool:
    """Sliding expiry for §十六 P1 session refresh."""
    r = Redis.from_url(redis_url, decode_responses=True)
    n = r.expire(redis_session_key(session_id), int(ttl_seconds))
    return bool(n)


def update_session_payload(redis_url: str, session_id: str, payload: HttpSessionPayload, ttl_seconds: int) -> bool:
    """Replace payload (e.g. after MFA verify) and refresh TTL."""
    r = Redis.from_url(redis_url, decode_responses=True)
    key = redis_session_key(session_id)
    if not r.exists(key):
        return False
    r.set(key, payload.to_json(), ex=int(ttl_seconds))
    return True
