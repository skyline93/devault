from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from devault.api.deps import get_db, require_admin
from devault.api.schemas import StorageProfileCreate, StorageProfileOut, StorageProfilePatch
from devault.security.auth_context import AuthContext
from devault.services import storage_profiles as storage_profiles_svc

router = APIRouter(prefix="/storage-profiles", tags=["storage-profiles"])


@router.get("", response_model=list[StorageProfileOut], summary="List storage profiles")
def list_storage_profiles(
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_admin),
) -> list[StorageProfileOut]:
    rows = storage_profiles_svc.list_profiles(db)
    return [StorageProfileOut.model_validate(storage_profiles_svc.profile_out_dict(r)) for r in rows]


@router.post("", response_model=StorageProfileOut, summary="Create storage profile")
def create_storage_profile(
    body: StorageProfileCreate,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_admin),
) -> StorageProfileOut:
    row = storage_profiles_svc.create_profile(
        db,
        name=body.name,
        slug=body.slug,
        storage_type=body.storage_type,
        is_active=body.is_active,
        local_root=body.local_root,
        s3_endpoint=body.s3_endpoint,
        s3_region=body.s3_region,
        s3_bucket=body.s3_bucket,
        s3_access_key_plain=body.s3_access_key,
        s3_secret_key_plain=body.s3_secret_key,
        s3_assume_role_arn=body.s3_assume_role_arn,
        s3_assume_role_external_id=body.s3_assume_role_external_id,
    )
    return StorageProfileOut.model_validate(storage_profiles_svc.profile_out_dict(row))


@router.get("/{profile_id}", response_model=StorageProfileOut, summary="Get storage profile")
def get_storage_profile(
    profile_id: uuid.UUID,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_admin),
) -> StorageProfileOut:
    row = storage_profiles_svc.require_profile(db, profile_id)
    return StorageProfileOut.model_validate(storage_profiles_svc.profile_out_dict(row))


@router.patch("/{profile_id}", response_model=StorageProfileOut, summary="Update storage profile")
def patch_storage_profile(
    profile_id: uuid.UUID,
    body: StorageProfilePatch,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_admin),
) -> StorageProfileOut:
    row = storage_profiles_svc.update_profile(
        db,
        profile_id,
        name=body.name,
        local_root=body.local_root,
        s3_endpoint=body.s3_endpoint,
        s3_region=body.s3_region,
        s3_bucket=body.s3_bucket,
        s3_access_key_plain=body.s3_access_key,
        s3_secret_key_plain=body.s3_secret_key,
        s3_assume_role_arn=body.s3_assume_role_arn,
        s3_assume_role_external_id=body.s3_assume_role_external_id,
    )
    return StorageProfileOut.model_validate(storage_profiles_svc.profile_out_dict(row))


@router.post("/{profile_id}/activate", response_model=StorageProfileOut, summary="Set active storage profile")
def activate_storage_profile(
    profile_id: uuid.UUID,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_admin),
) -> StorageProfileOut:
    row = storage_profiles_svc.set_active_profile(db, profile_id)
    return StorageProfileOut.model_validate(storage_profiles_svc.profile_out_dict(row))


@router.delete("/{profile_id}", status_code=204, summary="Delete storage profile")
def delete_storage_profile(
    profile_id: uuid.UUID,
    db: Session = Depends(get_db),
    _auth: AuthContext = Depends(require_admin),
) -> None:
    storage_profiles_svc.delete_profile(db, profile_id)
