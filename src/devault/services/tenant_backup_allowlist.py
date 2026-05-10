"""Union of enrolled Agents' reported backup path prefixes; optional tenant policy validation."""

from __future__ import annotations

import logging
import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from devault.db.models import AgentEnrollment, EdgeAgent, Tenant
from devault.observability.metrics import POLICY_ALLOWLIST_ENFORCE_REJECTS_TOTAL

logger = logging.getLogger(__name__)


def list_enrolled_agent_ids_for_tenant(db: Session, tenant_id: uuid.UUID) -> list[uuid.UUID]:
    tenant_s = str(tenant_id)
    out: list[uuid.UUID] = []
    for row in db.scalars(select(AgentEnrollment)).all():
        raw = row.allowed_tenant_ids or []
        allowed = {str(x) for x in raw}
        if tenant_s in allowed:
            out.append(row.agent_id)
    return out


def union_backup_path_allowlist_for_tenant(db: Session, tenant_id: uuid.UUID) -> list[str]:
    prefixes: set[str] = set()
    for aid in list_enrolled_agent_ids_for_tenant(db, tenant_id):
        edge = db.get(EdgeAgent, aid)
        if edge is None or not edge.backup_path_allowlist:
            continue
        for p in edge.backup_path_allowlist:
            s = str(p).strip().rstrip("/")
            if s:
                prefixes.add(s)
    return sorted(prefixes)


def path_under_allowlist_prefix(path: str, prefix: str) -> bool:
    p = path.rstrip("/") or "/"
    pre = prefix.rstrip("/") or "/"
    if p == pre:
        return True
    return p.startswith(pre + "/")


def validate_policy_paths_against_tenant_allowlist(
    db: Session,
    tenant_id: uuid.UUID,
    paths: list[str],
) -> None:
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        return
    mode = (tenant.policy_paths_allowlist_mode or "off").strip().lower()
    if mode not in ("off", "enforce", "warn"):
        mode = "off"
    if mode == "off":
        return
    union = union_backup_path_allowlist_for_tenant(db, tenant_id)
    if not union:
        return
    bad = [
        p.strip()
        for p in paths
        if p.strip() and not any(path_under_allowlist_prefix(p.strip(), pre) for pre in union)
    ]
    if not bad:
        return
    msg = (
        "Policy paths must fall under the union of backup path prefixes reported by Agents "
        f"enrolled for this tenant (Heartbeat). Offending paths: {bad!r}. "
        f"Current union: {union!r}. "
        f"Tenant policy_paths_allowlist_mode={mode!r}."
    )
    if mode == "enforce":
        POLICY_ALLOWLIST_ENFORCE_REJECTS_TOTAL.labels(tenant_id=str(tenant_id)).inc()
        raise HTTPException(status_code=400, detail=msg)
    logger.warning(msg)
