from __future__ import annotations

import json
import uuid

import pytest

from devault.security import agent_grpc_session as ags


class _FakeRedis:
    """Minimal Redis stub shared across ``from_url`` instances for unit tests."""

    store: dict[str, str] = {}
    counters: dict[str, int] = {}

    def __init__(self, *_a: object, **_kw: object) -> None:
        pass

    @classmethod
    def from_url(cls, _url: str, decode_responses: bool = True) -> _FakeRedis:
        return cls()

    def get(self, key: str) -> str | None:
        if key in self.store:
            return self.store[key]
        if key in self.counters:
            return str(self.counters[key])
        return None

    def setex(self, key: str, _ttl: int, value: str) -> None:
        self.store[key] = value

    def expire(self, key: str, _ttl: int) -> None:
        pass

    def delete(self, key: str) -> int:
        return 1 if self.store.pop(key, None) is not None else 0

    def incr(self, key: str) -> int:
        self.counters[key] = self.counters.get(key, 0) + 1
        v = self.counters[key]
        self.store[key] = str(v)
        return v


@pytest.fixture(autouse=True)
def _fake_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeRedis.store.clear()
    _FakeRedis.counters.clear()
    monkeypatch.setattr(ags, "Redis", _FakeRedis)


def test_mint_validate_refresh_revoke_roundtrip() -> None:
    aid = uuid.uuid4()
    url = "redis://fake/0"
    token, ttl = ags.mint_agent_session_token(url, agent_id=aid, ttl_seconds=3600)
    assert ttl == 3600
    assert token

    got = ags.validate_and_refresh_agent_session(url, token, ttl_seconds=3600)
    assert got == aid

    gen = ags.revoke_all_grpc_sessions_for_agent(url, aid)
    assert gen == 1

    assert ags.validate_and_refresh_agent_session(url, token, ttl_seconds=3600) is None


def test_validate_bad_token() -> None:
    assert ags.validate_and_refresh_agent_session("redis://fake/0", "nope", ttl_seconds=60) is None


def test_session_payload_invalid_json_deleted() -> None:
    aid = uuid.uuid4()
    sk = f"{ags.SESSION_KEY_PREFIX}badtok"
    _FakeRedis.store[sk] = "not-json"
    assert ags.validate_and_refresh_agent_session("redis://fake/0", "badtok", ttl_seconds=60) is None
