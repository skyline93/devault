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

from devault.api.deps import (
    UI_TENANT_COOKIE,
    get_db,
    get_effective_tenant_ui,
    require_admin_ui,
    require_write_ui,
    tenants_for_switcher_nav,
    verify_ui_basic_auth,
)
from devault.api.schemas import (
    CreateBackupJobBody,
    CreateRestoreDrillJobBody,
    CreateRestoreJobBody,
    FileBackupConfigV1,
    PolicyCreate,
    PolicyPatch,
    RestoreDrillScheduleCreate,
    RestoreDrillSchedulePatch,
    ScheduleCreate,
    SchedulePatch,
    TenantCreate,
    TenantPatch,
)
from devault.api.presenters import edge_agent_to_out
from devault.db.models import Artifact, EdgeAgent, Job, Policy, RestoreDrillSchedule, Schedule, Tenant
from devault.security.agent_grpc_session import revoke_all_grpc_sessions_for_agent
from devault.security.auth_context import AuthContext
from devault.settings import get_settings
from devault.services import control as control_svc

_PKG = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(_PKG / "web" / "templates"))

router = APIRouter(prefix="/ui", tags=["ui"])

_ui_dep = [Depends(verify_ui_basic_auth)]


def _lines(text: str | None) -> list[str]:
    return [ln.strip() for ln in (text or "").splitlines() if ln.strip()]


def _optional_int(raw: str) -> int | None:
    s = (raw or "").strip()
    if not s:
        return None
    return int(s)


def _file_backup_config_v1(
    *,
    paths_multiline: str,
    excludes_multiline: str,
    encrypt_artifacts: str,
    retention_days_raw: str,
    kms_envelope_key_id: str = "",
    object_lock_mode: str = "",
    object_lock_retain_days_raw: str = "",
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
    kms = (kms_envelope_key_id or "").strip()
    if kms:
        kwargs["kms_envelope_key_id"] = kms
    om = (object_lock_mode or "").strip()
    if om:
        kwargs["object_lock_mode"] = om
    ol_days = _optional_int(object_lock_retain_days_raw)
    if om and ol_days is not None:
        kwargs["object_lock_retain_days"] = ol_days
    return FileBackupConfigV1(**kwargs)


def _base_nav_kwargs(*, tenant: Tenant | None, db: Session, auth: AuthContext) -> dict:
    return {
        "current_tenant": tenant,
        "auth_ctx": auth,
        "tenant_switch_options": tenants_for_switcher_nav(db, auth),
    }


def _tpl(
    request: Request,
    name: str,
    *,
    tenant: Tenant | None,
    db: Session,
    auth: AuthContext,
    **page: object,
) -> HTMLResponse:
    ctx = dict(request=request, **page)
    ctx.update(_base_nav_kwargs(tenant=tenant, db=db, auth=auth))
    return templates.TemplateResponse(request, name, ctx)


def _redirect(
    path: str,
    *,
    flash: str | None = None,
    error: str | None = None,
    set_tenant_cookie: uuid.UUID | None = None,
    clear_tenant_cookie: bool = False,
) -> RedirectResponse:
    qs: list[str] = []
    if flash:
        qs.append(f"flash={quote(flash)}")
    if error:
        qs.append(f"error={quote(error)}")
    url = path + ("?" + "&".join(qs) if qs else "")
    r = RedirectResponse(url=url, status_code=303)
    half_year = int(86400 * 183)
    if set_tenant_cookie:
        r.set_cookie(
            key=UI_TENANT_COOKIE,
            value=str(set_tenant_cookie),
            path="/ui",
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=half_year,
        )
    if clear_tenant_cookie:
        r.delete_cookie(key=UI_TENANT_COOKIE, path="/ui")
    return r


def _http_err_detail(exc: HTTPException) -> str:
    d = exc.detail
    if isinstance(d, str):
        return d
    return str(d)


@router.get("/agents", response_class=HTMLResponse, dependencies=_ui_dep)
def ui_agents(
    request: Request,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant_ui),
    auth: AuthContext = Depends(verify_ui_basic_auth),
) -> HTMLResponse:
    """Fleet inventory (platform-wide; not scoped by tenant)."""
    rows = list(
        db.scalars(select(EdgeAgent).order_by(EdgeAgent.last_seen_at.desc()).limit(200)).all()
    )
    agents_out = [edge_agent_to_out(r) for r in rows]
    return _tpl(
        request,
        "agents.html",
        tenant=tenant,
        db=db,
        auth=auth,
        agents=agents_out,
        flash=request.query_params.get("flash"),
        error=request.query_params.get("error"),
    )


@router.post("/agents/{agent_id}/revoke-grpc-sessions", dependencies=_ui_dep)
def ui_agent_revoke_grpc_sessions(
    agent_id: uuid.UUID,
    db: Session = Depends(get_db),
    _admin: AuthContext = Depends(require_admin_ui),
) -> RedirectResponse:
    del _admin
    if db.get(EdgeAgent, agent_id) is None:
        return _redirect("/ui/agents", error="agent not found")
    settings = get_settings()
    gen = revoke_all_grpc_sessions_for_agent(settings.redis_url, agent_id)
    return _redirect("/ui/agents", flash=f"gRPC sessions revoked (generation={gen}).")


@router.get("/jobs", response_class=HTMLResponse, dependencies=_ui_dep)
def ui_jobs(
    request: Request,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant_ui),
    auth: AuthContext = Depends(verify_ui_basic_auth),
) -> HTMLResponse:
    rows = list(
        db.scalars(
            select(Job)
            .where(Job.tenant_id == tenant.id)
            .order_by(Job.created_at.desc())
            .limit(100)
        ).all()
    )
    return _tpl(
        request,
        "jobs.html",
        tenant=tenant,
        db=db,
        auth=auth,
        jobs=rows,
        flash=request.query_params.get("flash"),
        error=request.query_params.get("error"),
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
    auth: AuthContext = Depends(verify_ui_basic_auth),
) -> HTMLResponse:
    rows = list(
        db.scalars(
            select(Artifact)
            .where(Artifact.tenant_id == tenant.id)
            .order_by(Artifact.created_at.desc())
            .limit(100)
        ).all()
    )
    return _tpl(
        request,
        "artifacts.html",
        tenant=tenant,
        db=db,
        auth=auth,
        artifacts=rows,
        flash=request.query_params.get("flash"),
        error=request.query_params.get("error"),
    )


@router.post("/artifacts/{artifact_id}/legal-hold", dependencies=_ui_dep)
def ui_artifact_legal_hold(
    artifact_id: uuid.UUID,
    legal_hold: str = Form(...),
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant_ui),
    _admin: AuthContext = Depends(require_admin_ui),
) -> RedirectResponse:
    del _admin
    desired = legal_hold.strip().lower() in ("yes", "true", "1", "on")
    try:
        control_svc.patch_artifact_legal_hold(
            db,
            artifact_id,
            tenant_id=tenant.id,
            legal_hold=desired,
        )
        return _redirect("/ui/artifacts", flash=("Legal hold on." if desired else "Legal hold released."))
    except HTTPException as e:
        return _redirect("/ui/artifacts", error=_http_err_detail(e))


@router.post("/artifacts/restore-drill", dependencies=_ui_dep)
def ui_artifact_restore_drill(
    artifact_id: uuid.UUID = Form(),
    drill_base_path: str = Form(...),
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant_ui),
    _w: AuthContext = Depends(require_write_ui),
) -> RedirectResponse:
    try:
        body = CreateRestoreDrillJobBody(
            artifact_id=artifact_id,
            drill_base_path=drill_base_path.strip(),
        )
        job = control_svc.create_restore_drill_job(db, body, tenant_id=tenant.id)
        return _redirect("/ui/jobs", flash=f"Restore drill queued: job {job.id}")
    except HTTPException as e:
        return _redirect("/ui/artifacts", error=_http_err_detail(e))
    except ValidationError as e:
        return _redirect("/ui/artifacts", error=str(e.errors())[:600])


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
    auth: AuthContext = Depends(verify_ui_basic_auth),
) -> HTMLResponse:
    rows = list(
        db.scalars(
            select(Policy)
            .where(Policy.tenant_id == tenant.id)
            .order_by(Policy.created_at.desc())
        ).all()
    )
    return _tpl(
        request,
        "policies.html",
        tenant=tenant,
        db=db,
        auth=auth,
        policies=rows,
        flash=request.query_params.get("flash"),
        error=request.query_params.get("error"),
    )


@router.get("/policies/new", response_class=HTMLResponse, dependencies=_ui_dep)
def ui_policies_new(
    request: Request,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant_ui),
    auth: AuthContext = Depends(verify_ui_basic_auth),
) -> HTMLResponse:
    return _tpl(
        request,
        "policy_form.html",
        tenant=tenant,
        db=db,
        auth=auth,
        policy=None,
        flash=None,
        error=None,
        heading="New policy",
    )


@router.post("/policies/new", dependencies=_ui_dep)
def ui_policies_create(
    name: str = Form(...),
    paths_multiline: str = Form(...),
    excludes_multiline: str = Form(""),
    encrypt_artifacts: str = Form("no"),
    kms_envelope_key_id: str = Form(""),
    object_lock_mode: str = Form(""),
    object_lock_retain_days: str = Form(""),
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
            kms_envelope_key_id=kms_envelope_key_id,
            object_lock_mode=object_lock_mode,
            object_lock_retain_days_raw=object_lock_retain_days,
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
    auth: AuthContext = Depends(verify_ui_basic_auth),
) -> HTMLResponse:
    p = db.get(Policy, policy_id)
    if p is None or p.tenant_id != tenant.id:
        raise HTTPException(404, detail="policy not found")
    return _tpl(
        request,
        "policy_form.html",
        tenant=tenant,
        db=db,
        auth=auth,
        policy=p,
        flash=None,
        error=None,
        heading=f"Edit policy — {p.name}",
    )


@router.post("/policies/{policy_id}/edit", dependencies=_ui_dep)
def ui_policies_update(
    policy_id: uuid.UUID,
    name: str = Form(...),
    paths_multiline: str = Form(...),
    excludes_multiline: str = Form(""),
    encrypt_artifacts: str = Form("no"),
    kms_envelope_key_id: str = Form(""),
    object_lock_mode: str = Form(""),
    object_lock_retain_days: str = Form(""),
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
            kms_envelope_key_id=kms_envelope_key_id,
            object_lock_mode=object_lock_mode,
            object_lock_retain_days_raw=object_lock_retain_days,
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
    auth: AuthContext = Depends(verify_ui_basic_auth),
) -> HTMLResponse:
    rows = list(
        db.scalars(
            select(Schedule)
            .where(Schedule.tenant_id == tenant.id)
            .order_by(Schedule.created_at.desc())
        ).all()
    )
    return _tpl(
        request,
        "schedules.html",
        tenant=tenant,
        db=db,
        auth=auth,
        schedules=rows,
        flash=request.query_params.get("flash"),
        error=request.query_params.get("error"),
    )


@router.get("/schedules/new", response_class=HTMLResponse, dependencies=_ui_dep)
def ui_schedules_new(
    request: Request,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant_ui),
    auth: AuthContext = Depends(verify_ui_basic_auth),
) -> HTMLResponse:
    policies = list(
        db.scalars(
            select(Policy).where(Policy.tenant_id == tenant.id).order_by(Policy.name.asc())
        ).all()
    )
    return _tpl(
        request,
        "schedule_form.html",
        tenant=tenant,
        db=db,
        auth=auth,
        schedule=None,
        policies=policies,
        heading="New schedule",
        flash=request.query_params.get("flash"),
        error=request.query_params.get("error"),
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
    auth: AuthContext = Depends(verify_ui_basic_auth),
) -> HTMLResponse:
    s = db.get(Schedule, schedule_id)
    if s is None or s.tenant_id != tenant.id:
        raise HTTPException(404, detail="schedule not found")
    policies = list(
        db.scalars(
            select(Policy).where(Policy.tenant_id == tenant.id).order_by(Policy.name.asc())
        ).all()
    )
    return _tpl(
        request,
        "schedule_form.html",
        tenant=tenant,
        db=db,
        auth=auth,
        schedule=s,
        policies=policies,
        heading=f"Edit schedule — {schedule_id}",
        flash=request.query_params.get("flash"),
        error=request.query_params.get("error"),
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


@router.get("/restore-drill-schedules", response_class=HTMLResponse, dependencies=_ui_dep)
def ui_restore_drill_schedules(
    request: Request,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant_ui),
    auth: AuthContext = Depends(verify_ui_basic_auth),
) -> HTMLResponse:
    rows = list(
        db.scalars(
            select(RestoreDrillSchedule)
            .where(RestoreDrillSchedule.tenant_id == tenant.id)
            .order_by(RestoreDrillSchedule.created_at.desc())
        ).all()
    )
    return _tpl(
        request,
        "restore_drill_schedules.html",
        tenant=tenant,
        db=db,
        auth=auth,
        schedules=rows,
        flash=request.query_params.get("flash"),
        error=request.query_params.get("error"),
    )


@router.get("/restore-drill-schedules/new", response_class=HTMLResponse, dependencies=_ui_dep)
def ui_restore_drill_schedules_new(
    request: Request,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant_ui),
    auth: AuthContext = Depends(verify_ui_basic_auth),
) -> HTMLResponse:
    artifacts = list(
        db.scalars(
            select(Artifact).where(Artifact.tenant_id == tenant.id).order_by(Artifact.created_at.desc()).limit(200)
        ).all()
    )
    return _tpl(
        request,
        "restore_drill_schedule_form.html",
        tenant=tenant,
        db=db,
        auth=auth,
        schedule=None,
        artifacts=artifacts,
        heading="New restore drill schedule",
        flash=request.query_params.get("flash"),
        error=request.query_params.get("error"),
    )


@router.post("/restore-drill-schedules/new", dependencies=_ui_dep)
def ui_restore_drill_schedules_create(
    artifact_id: uuid.UUID = Form(...),
    drill_base_path: str = Form(...),
    cron_expression: str = Form(...),
    timezone: str = Form("UTC"),
    enabled: str = Form("yes"),
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant_ui),
    _w: AuthContext = Depends(require_write_ui),
) -> RedirectResponse:
    try:
        body = RestoreDrillScheduleCreate(
            artifact_id=artifact_id,
            drill_base_path=drill_base_path.strip(),
            cron_expression=cron_expression.strip(),
            timezone=(timezone or "UTC").strip(),
            enabled=enabled == "yes",
        )
        control_svc.create_restore_drill_schedule(db, body, tenant_id=tenant.id)
        return _redirect("/ui/restore-drill-schedules", flash="Restore drill schedule created.")
    except HTTPException as e:
        return _redirect("/ui/restore-drill-schedules", error=_http_err_detail(e))
    except ValidationError as e:
        return _redirect("/ui/restore-drill-schedules", error=str(e)[:800])


@router.get("/restore-drill-schedules/{schedule_id}/edit", response_class=HTMLResponse, dependencies=_ui_dep)
def ui_restore_drill_schedules_edit(
    request: Request,
    schedule_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant_ui),
    auth: AuthContext = Depends(verify_ui_basic_auth),
) -> HTMLResponse:
    s = db.get(RestoreDrillSchedule, schedule_id)
    if s is None or s.tenant_id != tenant.id:
        raise HTTPException(404, detail="restore drill schedule not found")
    artifacts = list(
        db.scalars(
            select(Artifact).where(Artifact.tenant_id == tenant.id).order_by(Artifact.created_at.desc()).limit(200)
        ).all()
    )
    return _tpl(
        request,
        "restore_drill_schedule_form.html",
        tenant=tenant,
        db=db,
        auth=auth,
        schedule=s,
        artifacts=artifacts,
        heading=f"Edit restore drill schedule — {schedule_id}",
        flash=request.query_params.get("flash"),
        error=request.query_params.get("error"),
    )


@router.post("/restore-drill-schedules/{schedule_id}/edit", dependencies=_ui_dep)
def ui_restore_drill_schedules_update(
    schedule_id: uuid.UUID,
    artifact_id: uuid.UUID = Form(...),
    drill_base_path: str = Form(...),
    cron_expression: str = Form(...),
    timezone: str = Form("UTC"),
    enabled: str = Form("yes"),
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant_ui),
    _w: AuthContext = Depends(require_write_ui),
) -> RedirectResponse:
    try:
        sch = db.get(RestoreDrillSchedule, schedule_id)
        if sch is None or sch.tenant_id != tenant.id:
            raise HTTPException(404, detail="restore drill schedule not found")
        patch = RestoreDrillSchedulePatch(
            artifact_id=artifact_id,
            drill_base_path=drill_base_path.strip(),
            cron_expression=cron_expression.strip(),
            timezone=(timezone or "UTC").strip(),
            enabled=enabled == "yes",
        )
        control_svc.patch_restore_drill_schedule(db, schedule_id, patch, tenant_id=tenant.id)
        return _redirect("/ui/restore-drill-schedules", flash="Restore drill schedule updated.")
    except HTTPException as e:
        return _redirect("/ui/restore-drill-schedules", error=_http_err_detail(e))
    except ValidationError as e:
        return _redirect("/ui/restore-drill-schedules", error=str(e)[:800])


@router.post("/restore-drill-schedules/{schedule_id}/delete", dependencies=_ui_dep)
def ui_restore_drill_schedules_delete(
    schedule_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant_ui),
    _w: AuthContext = Depends(require_write_ui),
) -> RedirectResponse:
    try:
        control_svc.delete_restore_drill_schedule(db, schedule_id, tenant_id=tenant.id)
        return _redirect("/ui/restore-drill-schedules", flash="Restore drill schedule deleted.")
    except HTTPException as e:
        return _redirect("/ui/restore-drill-schedules", error=_http_err_detail(e))


@router.post("/context/tenant", dependencies=_ui_dep)
def ui_context_tenant(
    tenant_id: str = Form(""),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(verify_ui_basic_auth),
) -> RedirectResponse:
    raw = (tenant_id or "").strip()
    if not raw:
        return _redirect("/ui/jobs", flash="Using default tenant (cookie cleared).", clear_tenant_cookie=True)
    try:
        tid = uuid.UUID(raw)
    except ValueError:
        return _redirect("/ui/jobs", error="invalid tenant id")
    auth.ensure_tenant_access(tid)
    row = db.get(Tenant, tid)
    if row is None:
        return _redirect("/ui/jobs", error="tenant not found")
    return _redirect("/ui/jobs", flash=f"Switched tenant: {row.slug}", set_tenant_cookie=row.id)


@router.get("/tenants", response_class=HTMLResponse, dependencies=_ui_dep)
def ui_tenants_list(
    request: Request,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant_ui),
    auth: AuthContext = Depends(require_admin_ui),
) -> HTMLResponse:
    rows = list(db.scalars(select(Tenant).order_by(Tenant.slug.asc())).all())
    return _tpl(
        request,
        "tenants.html",
        tenant=tenant,
        db=db,
        auth=auth,
        tenants=rows,
        flash=request.query_params.get("flash"),
        error=request.query_params.get("error"),
    )


@router.get("/tenants/new", response_class=HTMLResponse, dependencies=_ui_dep)
def ui_tenants_new_form(
    request: Request,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant_ui),
    auth: AuthContext = Depends(require_admin_ui),
) -> HTMLResponse:
    return _tpl(
        request,
        "tenant_form.html",
        tenant=tenant,
        db=db,
        auth=auth,
        row=None,
        heading="New tenant",
        flash=request.query_params.get("flash"),
        error=request.query_params.get("error"),
    )


@router.post("/tenants/new", dependencies=_ui_dep)
def ui_tenants_create(
    name: str = Form(...),
    slug: str = Form(...),
    db: Session = Depends(get_db),
    _admin: AuthContext = Depends(require_admin_ui),
) -> RedirectResponse:
    del _admin
    try:
        body = TenantCreate(name=name.strip(), slug=slug.strip())
        row = control_svc.create_tenant(db, body)
        return _redirect("/ui/tenants", flash=f"Created tenant {row.slug}.", set_tenant_cookie=row.id)
    except HTTPException as e:
        return _redirect("/ui/tenants/new", error=_http_err_detail(e))
    except ValidationError as e:
        return _redirect("/ui/tenants/new", error=str(e)[:800])


@router.get("/tenants/{edited_id}/edit", response_class=HTMLResponse, dependencies=_ui_dep)
def ui_tenants_edit_form(
    request: Request,
    edited_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant_ui),
    auth: AuthContext = Depends(require_admin_ui),
) -> HTMLResponse:
    row = db.get(Tenant, edited_id)
    if row is None:
        raise HTTPException(404, detail="tenant not found")
    return _tpl(
        request,
        "tenant_form.html",
        tenant=tenant,
        db=db,
        auth=auth,
        row=row,
        heading=f"Edit tenant — {row.slug}",
        flash=request.query_params.get("flash"),
        error=request.query_params.get("error"),
    )


def _patch_tenant_from_form(
    *,
    name: str,
    require_encrypted_artifacts: str,
    kms_envelope_key_id: str,
    s3_bucket: str,
    s3_assume_role_arn: str,
    s3_assume_role_external_id: str,
) -> TenantPatch:
    kms = (kms_envelope_key_id or "").strip()
    bkt = (s3_bucket or "").strip()
    arn = (s3_assume_role_arn or "").strip()
    ext = (s3_assume_role_external_id or "").strip()
    return TenantPatch(
        name=name.strip(),
        require_encrypted_artifacts=(require_encrypted_artifacts == "yes"),
        kms_envelope_key_id=kms if kms else "",
        s3_bucket=bkt if bkt else "",
        s3_assume_role_arn=arn if arn else "",
        s3_assume_role_external_id=ext if ext else "",
    )


@router.post("/tenants/{edited_id}/edit", dependencies=_ui_dep)
def ui_tenants_update(
    edited_id: uuid.UUID,
    name: str = Form(...),
    require_encrypted_artifacts: str = Form("no"),
    kms_envelope_key_id: str = Form(""),
    s3_bucket: str = Form(""),
    s3_assume_role_arn: str = Form(""),
    s3_assume_role_external_id: str = Form(""),
    db: Session = Depends(get_db),
    _admin: AuthContext = Depends(require_admin_ui),
) -> RedirectResponse:
    del _admin
    try:
        patch = _patch_tenant_from_form(
            name=name,
            require_encrypted_artifacts=require_encrypted_artifacts,
            kms_envelope_key_id=kms_envelope_key_id,
            s3_bucket=s3_bucket,
            s3_assume_role_arn=s3_assume_role_arn,
            s3_assume_role_external_id=s3_assume_role_external_id,
        )
        control_svc.patch_tenant(db, edited_id, patch)
        return _redirect("/ui/tenants", flash="Tenant updated.")
    except HTTPException as e:
        return _redirect(f"/ui/tenants/{edited_id}/edit", error=_http_err_detail(e))
    except ValidationError as e:
        return _redirect(f"/ui/tenants/{edited_id}/edit", error=str(e)[:800])
