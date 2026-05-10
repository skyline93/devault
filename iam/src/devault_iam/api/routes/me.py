from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from devault_iam.api.principal import Principal, get_current_principal

router = APIRouter(prefix="/v1", tags=["me"])


class MeOut(BaseModel):
    user_id: str
    email: str
    tenant_ids: list[str]
    permissions: list[str]
    principal_kind: str


@router.get("/me", response_model=MeOut)
def get_me(principal: Principal = Depends(get_current_principal)) -> MeOut:
    return MeOut(
        user_id=str(principal.user_id),
        email=principal.email,
        tenant_ids=[str(x) for x in sorted(principal.tenant_ids, key=lambda u: u.hex)],
        permissions=sorted(principal.permissions),
        principal_kind=principal.principal_kind,
    )
