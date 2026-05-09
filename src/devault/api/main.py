from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from devault import __version__
from devault.api.routes import agents, artifacts, jobs, policies, restore_drill_schedules, schedules, tenants, ui
from devault.grpc.server import start_grpc_server, stop_grpc_server
from devault.release_meta import GRPC_API_PACKAGE
from devault.observability.metrics import HTTP_REQUESTS_TOTAL
from devault.settings import get_settings

_OPENAPI_DESCRIPTION = """
REST API for the DeVault control plane: backup/restore **job** enqueue, **policy** and **schedule** management,
**artifact** listing, and Prometheus **metrics**. Jobs are executed by the edge **Agent** over gRPC with presigned
object storage URLs (see project documentation).
""".strip()

_OPENAPI_TAGS = [
    {
        "name": "jobs",
        "description": "Create and query backup, restore, and restore-drill jobs; cancel or retry when supported.",
    },
    {
        "name": "artifacts",
        "description": "List and fetch metadata for stored backup artifacts.",
    },
    {
        "name": "policies",
        "description": "CRUD for file backup policies (path lists, excludes, enabled flag).",
    },
    {
        "name": "schedules",
        "description": "CRUD for cron schedules attached to policies (driven by devault-scheduler).",
    },
    {
        "name": "restore-drill-schedules",
        "description": "Cron schedules that enqueue periodic restore drills (artifact recoverability checks on Agents).",
    },
    {
        "name": "tenants",
        "description": "List and create tenants; other resources are scoped per `X-DeVault-Tenant-Id` (or default slug).",
    },
    {
        "name": "ui",
        "description": "Minimal HTML UI (HTTP Basic = API token or DB API key): jobs, artifacts, policies, schedules, restore-drill schedules, agents fleet.",
    },
    {
        "name": "agents",
        "description": "Edge Agent fleet inventory (versions from gRPC Heartbeat / Register).",
    },
]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    start_grpc_server()
    yield
    stop_grpc_server()


app = FastAPI(
    title="DeVault API",
    description=_OPENAPI_DESCRIPTION,
    version=__version__,
    lifespan=lifespan,
    openapi_tags=_OPENAPI_TAGS,
)

app.include_router(agents.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(artifacts.router, prefix="/api/v1")
app.include_router(policies.router, prefix="/api/v1")
app.include_router(schedules.router, prefix="/api/v1")
app.include_router(restore_drill_schedules.router, prefix="/api/v1")
app.include_router(tenants.router, prefix="/api/v1")
app.include_router(ui.router)


@app.middleware("http")
async def _count_http_requests(request: Request, call_next):
    response = await call_next(request)
    route = request.scope.get("route")
    path_template = getattr(route, "path", request.url.path) if route else request.url.path
    HTTP_REQUESTS_TOTAL.labels(request.method, path_template).inc()
    return response


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/version")
def version() -> dict[str, str]:
    """Control plane release (HTTP); pair with Agent ``Heartbeat`` / ``Register`` version fields."""
    s = get_settings()
    body: dict[str, str] = {
        "service": "devault-api",
        "version": __version__,
        "api": "v1",
        "grpc_proto_package": GRPC_API_PACKAGE,
    }
    if s.server_git_sha:
        body["git_sha"] = s.server_git_sha
    return body
