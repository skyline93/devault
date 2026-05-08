from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from devault import __version__
from devault.api.routes import artifacts, jobs, policies, schedules, ui
from devault.grpc.server import start_grpc_server, stop_grpc_server

_OPENAPI_DESCRIPTION = """
REST API for the DeVault control plane: backup/restore **job** enqueue, **policy** and **schedule** management,
**artifact** listing, and Prometheus **metrics**. Jobs are executed by the edge **Agent** over gRPC with presigned
object storage URLs (see project documentation).
""".strip()

_OPENAPI_TAGS = [
    {
        "name": "jobs",
        "description": "Create and query backup/restore jobs; cancel or retry when supported.",
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
        "name": "ui",
        "description": "Minimal HTML forms for the same operations (HTTP Basic: password = DEVAULT_API_TOKEN).",
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

app.include_router(jobs.router, prefix="/api/v1")
app.include_router(artifacts.router, prefix="/api/v1")
app.include_router(policies.router, prefix="/api/v1")
app.include_router(schedules.router, prefix="/api/v1")
app.include_router(ui.router)


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
