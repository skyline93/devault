from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response

from devault_iam import __version__
from devault_iam.api.middleware import AccessLogAndMetricsMiddleware, RequestContextMiddleware
from devault_iam.api.principal import get_jwt_pem
from devault_iam.api.routes import api_keys as api_keys_routes
from devault_iam.api.routes import audit_logs as audit_logs_routes
from devault_iam.api.routes import auth as auth_routes
from devault_iam.api.routes import authorize as authorize_routes
from devault_iam.api.routes import me as me_routes
from devault_iam.api.routes import members as members_routes
from devault_iam.api.routes import platform_users as platform_users_routes
from devault_iam.api.routes import mfa as mfa_routes
from devault_iam.api.routes import ready as ready_routes
from devault_iam.api.routes import tenants as tenants_routes
from devault_iam.bootstrap import resolve_jwt_private_pem, resolve_jwt_public_pem
from devault_iam.security.dev_keys import generate_rsa_pem_keypair
from devault_iam.observability.prometheus_metrics import metrics_response_body
from devault_iam.security.jwt_tokens import public_pem_to_jwks
from devault_iam.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    settings.assert_production_config()
    priv = resolve_jwt_private_pem(settings).strip()
    pub = resolve_jwt_public_pem(settings).strip()
    if not priv or not pub:
        if settings.is_production():
            raise RuntimeError("JWT key material missing after production validation")
        priv, pub = generate_rsa_pem_keypair()
    app.state.jwt_private_pem = priv
    app.state.jwt_public_pem = pub
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="DeVault IAM",
        description="Identity, tenants, RBAC, and control-plane API keys for DeVault.",
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    app.add_middleware(AccessLogAndMetricsMiddleware)
    app.add_middleware(RequestContextMiddleware)
    origins = settings.cors_origin_list()
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(ready_routes.router)
    app.include_router(auth_routes.router)
    app.include_router(mfa_routes.router)
    app.include_router(tenants_routes.router)
    app.include_router(members_routes.router)
    app.include_router(me_routes.router)
    app.include_router(platform_users_routes.router)
    app.include_router(api_keys_routes.router)
    app.include_router(authorize_routes.router)
    app.include_router(audit_logs_routes.router)

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "devault-iam"}

    @app.get("/v1/meta", tags=["meta"])
    def meta() -> dict[str, str]:
        return {"service": "devault-iam", "version": __version__}

    @app.get("/.well-known/jwks.json", tags=["meta"])
    def jwks(request: Request) -> dict:
        _, pub = get_jwt_pem(request)
        return public_pem_to_jwks(pub, get_settings().jwt_key_id)

    @app.get("/metrics", tags=["meta"], include_in_schema=False)
    def prometheus_metrics() -> Response:
        s = get_settings()
        if not s.metrics_enabled:
            return Response(status_code=404)
        body, ct = metrics_response_body()
        return Response(content=body, media_type=ct)

    return app


app = create_app()
