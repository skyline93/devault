from __future__ import annotations

import json
import os
import sys
import time
import uuid

import httpx
import typer

app = typer.Typer(no_args_is_help=True, help="DeVault CLI (calls HTTP API)")
file_app = typer.Typer(no_args_is_help=True)
job_app = typer.Typer(no_args_is_help=True)
artifact_app = typer.Typer(no_args_is_help=True)

app.add_typer(file_app, name="file")
app.add_typer(job_app, name="job")
app.add_typer(artifact_app, name="artifact")


def _client() -> httpx.Client:
    base = os.environ.get("DEVAULT_API_BASE_URL", "http://127.0.0.1:8000")
    token = os.environ.get("DEVAULT_API_TOKEN")
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return httpx.Client(base_url=base, headers=headers, timeout=120.0)


@file_app.command("backup")
def file_backup(
    paths: list[str] = typer.Argument(..., help="Absolute paths to back up"),
    exclude: list[str] = typer.Option([], "--exclude", "-e", help="gitwildmatch exclude (repeatable)"),
) -> None:
    body = {"plugin": "file", "config": {"version": 1, "paths": paths, "excludes": list(exclude)}}
    with _client() as c:
        r = c.post("/api/v1/jobs/backup", json=body)
        r.raise_for_status()
        data = r.json()
    typer.echo(json.dumps(data, indent=2))


@file_app.command("restore")
def file_restore(
    artifact_id: str = typer.Argument(..., help="Artifact UUID"),
    to: str = typer.Option(..., "--to", help="Absolute target directory"),
    force: bool = typer.Option(False, "--force", help="Allow non-empty target"),
) -> None:
    body = {
        "artifact_id": artifact_id,
        "target_path": to,
        "confirm_overwrite_non_empty": force,
    }
    with _client() as c:
        r = c.post("/api/v1/jobs/restore", json=body)
        r.raise_for_status()
        data = r.json()
    typer.echo(json.dumps(data, indent=2))


@job_app.command("status")
def job_status(job_id: str) -> None:
    with _client() as c:
        r = c.get(f"/api/v1/jobs/{job_id}")
        r.raise_for_status()
        typer.echo(json.dumps(r.json(), indent=2))


@job_app.command("wait")
def job_wait(job_id: str, timeout_s: float = 300.0, poll: float = 1.0) -> None:
    deadline = time.monotonic() + timeout_s
    with _client() as c:
        while time.monotonic() < deadline:
            r = c.get(f"/api/v1/jobs/{job_id}")
            r.raise_for_status()
            data = r.json()
            st = data.get("status")
            if st in ("success", "failed"):
                typer.echo(json.dumps(data, indent=2))
                if st == "failed":
                    raise typer.Exit(code=1)
                return
            time.sleep(poll)
    typer.echo("timeout", err=True)
    raise typer.Exit(code=2)


@artifact_app.command("list")
def artifact_list() -> None:
    with _client() as c:
        r = c.get("/api/v1/artifacts")
        r.raise_for_status()
        typer.echo(json.dumps(r.json(), indent=2))


def main() -> None:
    try:
        app()
    except httpx.HTTPStatusError as e:
        typer.echo(e.response.text, err=True)
        raise typer.Exit(e.response.status_code) from e


if __name__ == "__main__":
    main()
