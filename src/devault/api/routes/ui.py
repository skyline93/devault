from __future__ import annotations

import uuid
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from devault.api.deps import get_db, get_effective_tenant_ui, require_write_ui, verify_ui_basic_auth
from devault.api.schemas import (
    CreateBackupJobBody,
    CreateRestoreJobBody,
    FileBackupConfigV1,
    PolicyCreate,
    PolicyPatch,
    ScheduleCreate,
    SchedulePatch,
)
from devault.api.presenters import edge_agent_to_out
from devault.db.models import Artifact, EdgeAgent, Job, Policy, Schedule, Tenant
from devault.security.auth_context import AuthContext
from devault.services import control as control_svc

_PKG = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(_PKG / "web" / "templates"))

router = APIRouter(prefix="/ui", tags=["ui"])

_ui_dep = [Depends(verify_ui_basic_auth)]


def _lines(text: str | None) -> list[str]:
    return [ln.strip() for ln in (text or "").splitlines() if ln.strip()]


def _file_backup_config_v1(
    *,
    paths_multiline: str,
    excludes_multiline: str,
    encrypt_artifacts: str,
    retention_days_raw: str,
) -> FileBackupConfigV1:
    paths = _lines(paths_multiline)
    excludes = _lines(excludes_multiline)
    rd = (retention_days_raw or "").strip()
    kwargs: dict = {
        "version": 1,
        "paths": paths,
        "excludes": excludes,
        "encrypt_artifacts": encrypt_artifacts == "yes",
    }
    if rd:
        kwargs["retention_days"] = int(rd)
    return FileBackupConfigV1(**kwargs)


def _redirect(path: str, *, flash: str | None = None, error: str | None = None) -> RedirectResponse:
    qs: list[str] = []
    if flash:
        qs.append(f"flash={quote(flash)}")
    if error:
        qs.append(f"error={quote(error)}")
    url = path + ("?" + "&".join(qs) if qs else "")
    return RedirectResponse(url=url, status_code=303)


def _http_err_detail(exc: HTTPException) -> str:
    d = exc.detail
    if isinstance(d, str):
        return d
    return str(d)


@router.get("/agents", response_class=HTMLResponse, dependencies=_ui_dep)
def ui_agents(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    """Fleet inventory (platform-wide; not scoped by tenant)."""
    rows = list(
        db.scalars(select(EdgeAgent).order_by(EdgeAgent.last_seen_at.desc()).limit(200)).all()
    )
    agents_out = [edge_agent_to_out(r) for r in rows]
    return templates.TemplateResponse(
        request,
        "agents.html",
        {
            "request": request,
            "agents": agents_out,
            "flash": request.query_params.get("flash"),
            "error": request.query_params.get("error"),
        },
    )


@router.get("/jobs", response_class=HTMLResponse, dependencies=_ui_dep)
def ui_jobs(
    request: Request,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant_ui),
) -> HTMLResponse:
    rows = list(
        db.scalars(
            select(Job)
            .where(Job.tenant_id == tenant.id)
            .order_by(Job.id.desc())
            .limit(100)
        ).all()
    )
    return templates.TemplateResponse(
        request,
        "jobs.html",
        {
            "request": request,
            "jobs": rows,
            "flash": request.query_params.get("flash"),
            "error": request.query_params.get("error"),
        },
    )


@router.post("/jobs/{job_id}/cancel", dependencies=_ui_dep)
def ui_job_cancel(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant_ui),
    _w: AuthContext = Depends(require_write_ui),
) -> RedirectResponse:
    try:
        control_svc.cancel_job(db, job_id, tenant_id=tenant.id)
        return _redirect("/ui/jobs", flash="Task cancelled.")
    except HTTPException as e:
        return _redirect("/ui/jobs", error=_http_err_detail(e))


@router.post("/jobs/{job_id}/retry", dependencies=_ui_dep)
def ui_job_retry(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant_ui),
    _w: AuthContext = Depends(require_write_ui),
) -> RedirectResponse:
    try:
        new_job = control_svc.retry_failed_backup_job(db, job_id, tenant_id=tenant.id)
        return _redirect("/ui/jobs", flash=f"Retry queued: {new_job.id}")
    except HTTPException as e:
        return _redirect("/ui/jobs", error=_http_err_detail(e))


@router.get("/artifacts", response_class=HTMLResponse, dependencies=_ui_dep)
def ui_artifacts(
    request: Request,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant_ui),
) -> HTMLResponse:
    rows = list(
        db.scalars(
            select(Artifact)
            .where(Artifact.tenant_id == tenant.id)
            .order_by(Artifact.created_at.desc())
            .limit(100)
        ).all()
    )
    return templates.TemplateResponse(
        request,
        "artifacts.html",
        {
            "request": request,
            "artifacts": rows,
            "flash": request.query_params.get("flash"),
            "error": request.query_params.get("error"),
        },
    )


@router.post("/artifacts/restore", dependencies=_ui_dep)
def ui_restore(
    artifact_id: uuid.UUID = Form(),
    target_path: str = Form(...),
    confirm_overwrite_non_empty: str = Form("no"),
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant_ui),
    _w: AuthContext = Depends(require_write_ui),
) -> RedirectResponse:
    try:
        body = CreateRestoreJobBody(
            artifact_id=artifact_id,
            target_path=target_path.strip(),
            confirm_overwrite_non_empty=confirm_overwrite_non_empty == "yes",
        )
        job = control_svc.create_restore_job(db, body, tenant_id=tenant.id)
        return _redirect("/ui/artifacts", flash=f"Restore queued: job {job.id}")
    except HTTPException as e:
        return _redirect("/ui/artifacts", error=_http_err_detail(e))
    except ValidationError as e:
        return _redirect("/ui/artifacts", error=str(e.errors())[:600])


@router.get("/policies", response_class=HTMLResponse, dependencies=_ui_dep)
def ui_policies(
    request: Request,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant_ui),
) -> HTMLResponse:
    rows = list(
        db.scalars(
            select(Policy)
            .where(Policy.tenant_id == tenant.id)
            .order_by(Policy.created_at.desc())
        ).all()
    )
    return templates.TemplateResponse(
        request,
        "policies.html",
        {
            "request": request,
            "policies": rows,
            "flash": request.query_params.get("flash"),
            "error": request.query_params.get("error"),
        },
    )


@router.get("/policies/new", response_class=HTMLResponse, dependencies=_ui_dep)
def ui_policies_new(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    _ = db
    return templates.TemplateResponse(
        request,
        "policy_form.html",
        {
            "request": request,
            "policy": None,
            "flash": None,
            "error": None,
            "heading": "New policy",
        },
    )


@router.post("/policies/new", dependencies=_ui_dep)
def ui_policies_create(
    name: str = Form(...),
    paths_multiline: str = Form(...),
    excludes_multiline: str = Form(""),
    encrypt_artifacts: str = Form("no"),
    retention_days: str = Form(""),
    enabled: str = Form("yes"),
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant_ui),
    _w: AuthContext = Depends(require_write_ui),
) -> RedirectResponse:
    try:
        cfg = _file_backup_config_v1(
            paths_multiline=paths_multiline,
            excludes_multiline=excludes_multiline,
            encrypt_artifacts=encrypt_artifacts,
            retention_days_raw=retention_days,
        )
        body = PolicyCreate(
            name=name.strip(),
            plugin="file",
            config=cfg,
            enabled=enabled == "yes",
        )
        control_svc.create_policy(db, body, tenant_id=tenant.id)
        return _redirect("/ui/policies", flash="Policy created.")
    except HTTPException as e:
        return _redirect("/ui/policies", error=_http_err_detail(e))
    except (ValidationError, ValueError) as e:
        return _redirect("/ui/policies", error=str(e)[:800])


@router.get("/policies/{policy_id}/edit", response_class=HTMLResponse, dependencies=_ui_dep)
def ui_policies_edit(
    request: Request,
    policy_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant_ui),
) -> HTMLResponse:
    p = db.get(Policy, policy_id)
    if p is None or p.tenant_id != tenant.id:
        raise HTTPException(404, detail="policy not found")
    return templates.TemplateResponse(
        request,
        "policy_form.html",
        {
            "request": request,
            "policy": p,
            "flash": None,
            "error": None,
            "heading": f"Edit policy — {p.name}",
        },
    )


@router.post("/policies/{policy_id}/edit", dependencies=_ui_dep)
def ui_policies_update(
    policy_id: uuid.UUID,
    name: str = Form(...),
    paths_multiline: str = Form(...),
    excludes_multiline: str = Form(""),
    encrypt_artifacts: str = Form("no"),
    retention_days: str = Form(""),
    enabled: str = Form("yes"),
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant_ui),
    _w: AuthContext = Depends(require_write_ui),
) -> RedirectResponse:
    try:
        cfg = _file_backup_config_v1(
            paths_multiline=paths_multiline,
            excludes_multiline=excludes_multiline,
            encrypt_artifacts=encrypt_artifacts,
            retention_days_raw=retention_days,
        )
        patch = PolicyPatch(name=name.strip(), config=cfg, enabled=enabled == "yes")
        control_svc.patch_policy(db, policy_id, patch, tenant_id=tenant.id)
        return _redirect("/ui/policies", flash="Policy updated.")
    except HTTPException as e:
        return _redirect("/ui/policies", error=_http_err_detail(e))
    except (ValidationError, ValueError) as e:
        return _redirect("/ui/policies", error=str(e)[:800])


@router.post("/policies/{policy_id}/delete", dependencies=_ui_dep)
def ui_policies_delete(
    policy_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant_ui),
    _w: AuthContext = Depends(require_write_ui),
) -> RedirectResponse:
    try:
        control_svc.delete_policy(db, policy_id, tenant_id=tenant.id)
        return _redirect("/ui/policies", flash="Policy deleted.")
    except HTTPException as e:
        return _redirect("/ui/policies", error=_http_err_detail(e))


@router.post("/policies/run-backup", dependencies=_ui_dep)
def ui_run_policy_backup(
    policy_id: uuid.UUID = Form(...),
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant_ui),
    _w: AuthContext = Depends(require_write_ui),
) -> RedirectResponse:
    try:
        body = CreateBackupJobBody(plugin="file", policy_id=policy_id)
        job = control_svc.create_backup_job(db, body, tenant_id=tenant.id)
        return _redirect("/ui/jobs", flash=f"Backup queued: job {job.id}")
    except HTTPException as e:
        return _redirect("/ui/policies", error=_http_err_detail(e))
    except ValidationError as e:
        return _redirect("/ui/policies", error=str(e)[:800])


@router.get("/schedules", response_class=HTMLResponse, dependencies=_ui_dep)
def ui_schedules(
    request: Request,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant_ui),
) -> HTMLResponse:
    rows = list(
        db.scalars(
            select(Schedule)
            .where(Schedule.tenant_id == tenant.id)
            .order_by(Schedule.created_at.desc())
        ).all()
    )
    return templates.TemplateResponse(
        request,
        "schedules.html",
        {
            "request": request,
            "schedules": rows,
            "flash": request.query_params.get("flash"),
            "error": request.query_params.get("error"),
        },
    )


@router.get("/schedules/new", response_class=HTMLResponse, dependencies=_ui_dep)
def ui_schedules_new(
    request: Request,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant_ui),
) -> HTMLResponse:
    policies = list(
        db.scalars(
            select(Policy).where(Policy.tenant_id == tenant.id).order_by(Policy.name.asc())
        ).all()
    )
    return templates.TemplateResponse(
        request,
        "schedule_form.html",
        {
            "request": request,
            "schedule": None,
            "policies": policies,
            "heading": "New schedule",
        },
    )


@router.post("/schedules/new", dependencies=_ui_dep)
def ui_schedules_create(
    policy_id: uuid.UUID = Form(...),
    cron_expression: str = Form(...),
    timezone: str = Form("UTC"),
    enabled: str = Form("yes"),
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant_ui),
    _w: AuthContext = Depends(require_write_ui),
) -> RedirectResponse:
    try:
        body = ScheduleCreate(
            policy_id=policy_id,
            cron_expression=cron_expression.strip(),
            timezone=timezone.strip() or "UTC",
            enabled=enabled == "yes",
        )
        control_svc.create_schedule(db, body, tenant_id=tenant.id)
        return _redirect("/ui/schedules", flash="Schedule created.")
    except HTTPException as e:
        return _redirect("/ui/schedules", error=_http_err_detail(e))
    except ValidationError as e:
        return _redirect("/ui/schedules", error=str(e)[:800])


@router.get("/schedules/{schedule_id}/edit", response_class=HTMLResponse, dependencies=_ui_dep)
def ui_schedules_edit(
    request: Request,
    schedule_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant_ui),
) -> HTMLResponse:
    s = db.get(Schedule, schedule_id)
    if s is None or s.tenant_id != tenant.id:
        raise HTTPException(404, detail="schedule not found")
    policies = list(
        db.scalars(
            select(Policy).where(Policy.tenant_id == tenant.id).order_by(Policy.name.asc())
        ).all()
    )
    return templates.TemplateResponse(
        request,
        "schedule_form.html",
        {
            "request": request,
            "schedule": s,
            "policies": policies,
            "heading": f"Edit schedule — {schedule_id}",
        },
    )


@router.post("/schedules/{schedule_id}/edit", dependencies=_ui_dep)
def ui_schedules_update(
    schedule_id: uuid.UUID,
    cron_expression: str = Form(...),
    timezone: str = Form("UTC"),
    enabled: str = Form("yes"),
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant_ui),
    _w: AuthContext = Depends(require_write_ui),
) -> RedirectResponse:
    try:
        sch = db.get(Schedule, schedule_id)
        if sch is None or sch.tenant_id != tenant.id:
            raise HTTPException(404, detail="schedule not found")
        patch = SchedulePatch(
            cron_expression=cron_expression.strip(),
            timezone=(timezone or "UTC").strip(),
            enabled=enabled == "yes",
        )
        control_svc.patch_schedule(db, schedule_id, patch, tenant_id=tenant.id)
        return _redirect("/ui/schedules", flash="Schedule updated.")
    except HTTPException as e:
        return _redirect("/ui/schedules", error=_http_err_detail(e))


@router.post("/schedules/{schedule_id}/delete", dependencies=_ui_dep)
def ui_schedules_delete(
    schedule_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant_ui),
    _w: AuthContext = Depends(require_write_ui),
) -> RedirectResponse:
    try:
        control_svc.delete_schedule(db, schedule_id, tenant_id=tenant.id)
        return _redirect("/ui/schedules", flash="Schedule deleted.")
    except HTTPException as e:
        return _redirect("/ui/schedules", error=_http_err_detail(e))
