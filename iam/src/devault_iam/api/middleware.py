from __future__ import annotations

import json
import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from devault_iam.observability.prometheus_metrics import (
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_TOTAL,
)
from devault_iam.settings import get_settings

_access_logger = logging.getLogger("devault_iam.access")


def _route_path(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None) if route is not None else None
    if isinstance(path, str) and path:
        return path
    return request.url.path


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assign ``request.state.request_id`` (from ``X-Request-Id`` or generated) and echo on response."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        hdr = (request.headers.get("x-request-id") or "").strip()
        if hdr and len(hdr) <= 80:
            rid = hdr
        else:
            rid = uuid.uuid4().hex
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["X-Request-Id"] = rid
        return response


class AccessLogAndMetricsMiddleware(BaseHTTPMiddleware):
    """Structured access log + Prometheus counters/histograms (path from matched route when available)."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        settings = get_settings()
        t0 = time.perf_counter()
        path = _route_path(request)
        method = request.method
        rid = getattr(request.state, "request_id", None)
        try:
            response = await call_next(request)
        except Exception:
            elapsed = time.perf_counter() - t0
            if settings.metrics_enabled:
                HTTP_REQUESTS_TOTAL.labels(method=method, path=path, status="500").inc()
                HTTP_REQUEST_DURATION_SECONDS.labels(method=method, path=path).observe(elapsed)
            if settings.http_access_log_enabled:
                _log_line(
                    settings,
                    method=method,
                    path=path,
                    status=500,
                    elapsed_s=elapsed,
                    request_id=rid,
                )
            raise
        elapsed = time.perf_counter() - t0
        status = response.status_code
        if settings.metrics_enabled:
            HTTP_REQUESTS_TOTAL.labels(method=method, path=path, status=str(status)).inc()
            HTTP_REQUEST_DURATION_SECONDS.labels(method=method, path=path).observe(elapsed)
        if settings.http_access_log_enabled:
            _log_line(
                settings,
                method=method,
                path=path,
                status=status,
                elapsed_s=elapsed,
                request_id=rid,
            )
        return response


def _log_line(
    settings,
    *,
    method: str,
    path: str,
    status: int,
    elapsed_s: float,
    request_id: str | None,
) -> None:
    if settings.access_log_json:
        payload = {
            "msg": "http_access",
            "method": method,
            "path": path,
            "status": status,
            "elapsed_ms": round(elapsed_s * 1000, 3),
            "request_id": request_id,
        }
        _access_logger.info(json.dumps(payload, ensure_ascii=False))
    else:
        _access_logger.info(
            "%s %s %s %.3fms request_id=%s",
            method,
            path,
            status,
            elapsed_s * 1000,
            request_id or "-",
        )
