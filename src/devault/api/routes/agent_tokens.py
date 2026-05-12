from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from devault.api.deps import get_auth_context, get_db, get_effective_tenant, require_write
from devault.api.schemas import AgentTokenCreate, AgentTokenCreatedOut, AgentTokenOut, AgentTokenPatch
from devault.db.models import AgentToken, Tenant
from devault.security.auth_context import AuthContext
from devault.services.agent_tokens import count_instances_for_token, create_agent_token, set_agent_token_disabled

router = APIRouter(prefix="/agent-tokens", tags=["agent-tokens"])


def _token_out(db: Session, row: AgentToken) -> AgentTokenOut:
    return AgentTokenOut(
        id=row.id,
        tenant_id=row.tenant_id,
        label=row.label,
        description=row.description,
        expires_at=row.expires_at,
        disabled_at=row.disabled_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
        last_used_at=row.last_used_at,
        instance_count=count_instances_for_token(db, row.id),
    )


@router.post("", response_model=AgentTokenCreatedOut, summary="Create tenant Agent token (plaintext once)")
def create_token(
    body: AgentTokenCreate,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant),
    auth: AuthContext = Depends(require_write),
) -> AgentTokenCreatedOut:
    del auth
    row, plaintext = create_agent_token(
        db,
        tenant_id=tenant.id,
        label=body.label,
        description=body.description,
        expires_at=body.expires_at,
    )
    db.commit()
    db.refresh(row)
    return AgentTokenCreatedOut(
        id=row.id,
        tenant_id=row.tenant_id,
        label=row.label,
        description=row.description,
        expires_at=row.expires_at,
        created_at=row.created_at,
        plaintext_secret=plaintext,
        instance_count=0,
    )


@router.get("", response_model=list[AgentTokenOut], summary="List Agent tokens for the effective tenant")
def list_tokens(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant),
    auth: AuthContext = Depends(get_auth_context),
) -> list[AgentTokenOut]:
    del auth
    rows = list(
        db.scalars(
            select(AgentToken).where(AgentToken.tenant_id == tenant.id).order_by(AgentToken.created_at.desc()),
        ).all(),
    )
    return [_token_out(db, row) for row in rows]


@router.get("/{token_id}", response_model=AgentTokenOut, summary="Get one Agent token")
def get_token(
    token_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant),
    auth: AuthContext = Depends(get_auth_context),
) -> AgentTokenOut:
    del auth
    row = db.get(AgentToken, token_id)
    if row is None or row.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="agent token not found")
    return _token_out(db, row)


@router.patch("/{token_id}", response_model=AgentTokenOut, summary="Update token label/description")
def patch_token(
    token_id: uuid.UUID,
    body: AgentTokenPatch,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant),
    auth: AuthContext = Depends(require_write),
) -> AgentTokenOut:
    del auth
    row = db.get(AgentToken, token_id)
    if row is None or row.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="agent token not found")
    if body.label is not None:
        row.label = body.label.strip()
    if body.description is not None:
        row.description = body.description.strip() or None
    db.commit()
    db.refresh(row)
    return _token_out(db, row)


@router.post("/{token_id}/disable", response_model=AgentTokenOut, summary="Disable an Agent token")
def disable_token(
    token_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant),
    auth: AuthContext = Depends(require_write),
) -> AgentTokenOut:
    del auth
    row = db.get(AgentToken, token_id)
    if row is None or row.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="agent token not found")
    set_agent_token_disabled(db, row, disabled=True)
    db.commit()
    db.refresh(row)
    return _token_out(db, row)


@router.post("/{token_id}/enable", response_model=AgentTokenOut, summary="Re-enable a disabled Agent token")
def enable_token(
    token_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_effective_tenant),
    auth: AuthContext = Depends(require_write),
) -> AgentTokenOut:
    del auth
    row = db.get(AgentToken, token_id)
    if row is None or row.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="agent token not found")
    set_agent_token_disabled(db, row, disabled=False)
    db.commit()
    db.refresh(row)
    return _token_out(db, row)
