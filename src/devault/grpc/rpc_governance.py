"""Per-RPC rate limiting and structured audit logging for the Agent gRPC service."""

from __future__ import annotations

import json
import logging
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import grpc

from devault.settings import Settings

_audit_logger = logging.getLogger("devault.grpc.audit")


class TokenBucket:
    """Simple token bucket keyed by gRPC peer() string (thread-safe)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state: dict[str, tuple[float, float]] = {}

    def allow(self, peer: str, *, rps: float, burst: float) -> bool:
        if rps <= 0:
            return True
        burst = max(burst, 1.0)
        now = time.monotonic()
        with self._lock:
            tokens, last = self._state.get(peer, (burst, now))
            tokens = min(burst, tokens + (now - last) * rps)
            if tokens < 1.0:
                self._state[peer] = (tokens, now)
                return False
            tokens -= 1.0
            self._state[peer] = (tokens, now)
            return True


_bucket = TokenBucket()


@contextmanager
def grpc_governance(
    rpc_name: str,
    context: grpc.ServicerContext,
    settings: Settings,
    *,
    audit_extra: dict[str, Any] | None = None,
) -> Iterator[None]:
    """Rate-limit then emit one JSON audit line per RPC (success or failure)."""
    peer = context.peer() or "unknown"
    if not _bucket.allow(
        peer,
        rps=float(settings.grpc_rps_per_peer),
        burst=float(settings.grpc_rps_burst_per_peer),
    ):
        context.abort(grpc.StatusCode.RESOURCE_EXHAUSTED, "grpc rate limit exceeded")
        raise RuntimeError("unreachable")

    t0 = time.perf_counter()
    code_name = "OK"
    try:
        yield
    finally:
        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)
        code_name = "UNKNOWN"
        try:
            code_fn = getattr(context, "code", None)
            if callable(code_fn):
                code = code_fn()
                if code is not None:
                    code_name = code.name
        except Exception:
            code_name = "UNKNOWN"
        if settings.grpc_audit_log:
            payload: dict[str, Any] = {
                "rpc": rpc_name,
                "peer": peer,
                "grpc_code": code_name,
                "elapsed_ms": elapsed_ms,
            }
            if audit_extra:
                payload["extra"] = audit_extra
            _audit_logger.info(json.dumps(payload, default=str))
