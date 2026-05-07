from __future__ import annotations

from fastapi import FastAPI

from devault import __version__
from devault.api.routes import artifacts, jobs

app = FastAPI(title="DeVault API", version=__version__)

app.include_router(jobs.router, prefix="/api/v1")
app.include_router(artifacts.router, prefix="/api/v1")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
