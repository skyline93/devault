from __future__ import annotations

import secrets
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from devault.settings import Settings, get_settings

CSRF_EXEMPT_PATHS: frozenset[str] = frozenset(
    {
        "/api/v1/auth/login",
        "/api/v1/auth/logout",
        "/api/v1/auth/register",
        "/api/v1/auth/password-reset/request",
        "/api/v1/auth/password-reset/confirm",
        "/api/v1/auth/invitations/accept",
    }
)


class CsrfProtectionMiddleware(BaseHTTPMiddleware):
    """§十六-04: double-submit cookie for browser session users on mutating /api/v1 calls."""

    def __init__(self, app: Callable[..., Awaitable[Response]], settings: Settings | None = None) -> None:
        super().__init__(app)
        self._settings = settings

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        settings = self._settings or get_settings()
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            path = request.url.path
            if path.startswith("/api/v1") and path not in CSRF_EXEMPT_PATHS:
                if request.cookies.get(settings.session_cookie_name):
                    hdr = request.headers.get("X-CSRF-Token")
                    ck = request.cookies.get(settings.csrf_cookie_name)
                    if not hdr or not ck or not secrets.compare_digest(str(hdr), str(ck)):
                        return JSONResponse(
                            status_code=403,
                            content={"detail": "CSRF token missing or invalid"},
                        )
        return await call_next(request)
