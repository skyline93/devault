"""DB-backed storage profiles: active row resolution, encryption, and ``S3ConnSpec`` materialization."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import desc, select, update
from sqlalchemy.orm import Session

from devault.crypto.storage_secrets import decrypt_optional, encrypt_optional, fernet_from_master_key
from devault.db.models import Artifact, StorageProfile
from devault.settings import Settings

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")


def _infer_s3_use_ssl(endpoint: str | None) -> bool:
    e = (endpoint or "").strip().lower()
    if e.startswith("http://"):
        return False
    return True


def _allocate_s3_slug(db: Session, explicit: str | None) -> str:
    if explicit and (s := explicit.strip().lower()) and _SLUG_RE.match(s):
        if db.scalar(select(StorageProfile.id).where(StorageProfile.slug == s).limit(1)):
            raise HTTPException(status_code=400, detail="slug already exists")
        return s
    for _ in range(48):
        cand = f"s3-{uuid.uuid4().hex[:12]}"
        if not db.scalar(select(StorageProfile.id).where(StorageProfile.slug == cand).limit(1)):
            return cand
    raise HTTPException(status_code=500, detail="could not allocate storage profile slug")


def get_active_profile(db: Session) -> StorageProfile | None:
    return db.scalars(select(StorageProfile).where(StorageProfile.is_active.is_(True)).limit(1)).first()


def require_active_profile(db: Session) -> StorageProfile:
    row = get_active_profile(db)
    if row is None:
        raise ValueError("no active storage profile configured")
    return row


def get_profile(db: Session, profile_id: uuid.UUID) -> StorageProfile | None:
    return db.get(StorageProfile, profile_id)


def require_profile(db: Session, profile_id: uuid.UUID) -> StorageProfile:
    row = get_profile(db, profile_id)
    if row is None:
        raise HTTPException(status_code=404, detail="storage profile not found")
    return row


def list_profiles(db: Session) -> list[StorageProfile]:
    return list(db.scalars(select(StorageProfile).order_by(desc(StorageProfile.created_at))).all())


def s3_conn_spec_from_profile(profile: StorageProfile, settings: Settings) -> "S3ConnSpec":
    from devault.storage.s3_client import S3ConnSpec

    if profile.storage_type != "s3":
        raise ValueError("storage profile is not s3")
    if not (profile.s3_endpoint or "").strip():
        raise ValueError("s3_endpoint is required for s3 storage profiles")
    if not (profile.s3_bucket or "").strip():
        raise ValueError("s3_bucket is required for s3 storage profiles")

    fnt = fernet_from_master_key()
    ak = sk = None
    if profile.encrypted_access_key:
        if fnt is None:
            raise ValueError("DEVAULT_STORAGE_CONFIG_MASTER_KEY is required to decrypt storage credentials")
        ak = decrypt_optional(profile.encrypted_access_key, fnt)
    if profile.encrypted_secret_key:
        if fnt is None:
            raise ValueError("DEVAULT_STORAGE_CONFIG_MASTER_KEY is required to decrypt storage credentials")
        sk = decrypt_optional(profile.encrypted_secret_key, fnt)

    return S3ConnSpec(
        endpoint=(profile.s3_endpoint or "").strip(),
        region=(profile.s3_region or "us-east-1").strip(),
        use_ssl=bool(profile.s3_use_ssl),
        bucket=(profile.s3_bucket or "").strip(),
        access_key=ak,
        secret_key=sk,
        assume_role_arn=(profile.s3_assume_role_arn or "").strip() or None,
        assume_role_external_id=(profile.s3_assume_role_external_id or "").strip() or None,
    )


def validate_profile_fields(
    *,
    storage_type: str,
    local_root: str | None,
    s3_endpoint: str | None,
    s3_bucket: str | None,
) -> None:
    st = storage_type.strip().lower()
    if st not in ("s3", "local"):
        raise HTTPException(400, detail="storage_type must be s3 or local")
    if st == "local":
        if not (local_root or "").strip():
            raise HTTPException(400, detail="local_root is required for local storage profiles")
    if st == "s3":
        if not (s3_endpoint or "").strip() or not (s3_bucket or "").strip():
            raise HTTPException(400, detail="s3_endpoint and s3_bucket are required for s3 storage profiles")


def create_profile(
    db: Session,
    *,
    name: str | None,
    slug: str | None,
    storage_type: str,
    is_active: bool,
    local_root: str | None,
    s3_endpoint: str | None,
    s3_region: str | None,
    s3_bucket: str | None,
    s3_access_key_plain: str | None,
    s3_secret_key_plain: str | None,
    s3_assume_role_arn: str | None,
    s3_assume_role_external_id: str | None,
) -> StorageProfile:
    st = storage_type.strip().lower()
    validate_profile_fields(storage_type=st, local_root=local_root, s3_endpoint=s3_endpoint, s3_bucket=s3_bucket)

    if st == "local":
        slug_n = (slug or "").strip().lower()
        if not slug_n or not _SLUG_RE.match(slug_n):
            raise HTTPException(400, detail="slug must be lowercase alphanumeric with hyphens (1–63 chars)")
        if db.scalar(select(StorageProfile.id).where(StorageProfile.slug == slug_n).limit(1)):
            raise HTTPException(400, detail="slug already exists")
        name_f = (name or "").strip()
        if not name_f:
            raise HTTPException(400, detail="name is required for local storage profiles")
        s3_ep = None
        s3_reg = None
        s3_bkt = None
        use_ssl = False
    else:
        slug_n = _allocate_s3_slug(db, slug)
        bucket = (s3_bucket or "").strip()
        name_f = (name or "").strip() or bucket or slug_n
        s3_ep = (s3_endpoint.strip() if s3_endpoint else None) or None
        s3_reg = (s3_region or "").strip() or None
        s3_bkt = (s3_bucket.strip() if s3_bucket else None) or None
        use_ssl = _infer_s3_use_ssl(s3_endpoint)

    fnt = fernet_from_master_key()
    enc_ak = enc_sk = None
    if st == "s3":
        if fnt is None:
            raise HTTPException(400, detail="DEVAULT_STORAGE_CONFIG_MASTER_KEY is required to store static keys")
        ak = (s3_access_key_plain or "").strip() or None
        sk = (s3_secret_key_plain or "").strip() or None
        if not ak or not sk:
            raise HTTPException(400, detail="s3_access_key and s3_secret_key are required for s3 storage profiles")
        enc_ak = encrypt_optional(ak, fnt)
        enc_sk = encrypt_optional(sk, fnt)
    elif (s3_access_key_plain or "").strip() or (s3_secret_key_plain or "").strip():
        if fnt is None:
            raise HTTPException(400, detail="DEVAULT_STORAGE_CONFIG_MASTER_KEY is required to store static keys")
        ak = (s3_access_key_plain or "").strip() or None
        sk = (s3_secret_key_plain or "").strip() or None
        if (ak is None) ^ (sk is None):
            raise HTTPException(400, detail="s3 access key and secret key must be set together or both omitted")
        if ak and sk:
            enc_ak = encrypt_optional(ak, fnt)
            enc_sk = encrypt_optional(sk, fnt)

    row = StorageProfile(
        id=uuid.uuid4(),
        name=name_f,
        slug=slug_n,
        storage_type=st,
        is_active=False,
        local_root=(local_root.strip() if local_root else None) or None,
        s3_endpoint=s3_ep,
        s3_region=s3_reg,
        s3_bucket=s3_bkt,
        s3_use_ssl=use_ssl,
        encrypted_access_key=enc_ak,
        encrypted_secret_key=enc_sk,
        s3_assume_role_arn=(s3_assume_role_arn.strip() if s3_assume_role_arn else None) or None,
        s3_assume_role_external_id=(s3_assume_role_external_id.strip() if s3_assume_role_external_id else None)
        or None,
    )
    db.add(row)
    db.flush()
    if is_active:
        out = set_active_profile(db, row.id)
        return out
    db.commit()
    db.refresh(row)
    return row


def update_profile(
    db: Session,
    profile_id: uuid.UUID,
    *,
    name: str | None,
    local_root: str | None,
    s3_endpoint: str | None,
    s3_region: str | None,
    s3_bucket: str | None,
    s3_access_key_plain: str | None,
    s3_secret_key_plain: str | None,
    s3_assume_role_arn: str | None,
    s3_assume_role_external_id: str | None,
) -> StorageProfile:
    row = require_profile(db, profile_id)
    if name is not None:
        row.name = name.strip()
    if local_root is not None:
        row.local_root = local_root.strip() or None
    if s3_endpoint is not None:
        row.s3_endpoint = s3_endpoint.strip() or None
        if row.storage_type == "s3":
            row.s3_use_ssl = _infer_s3_use_ssl(row.s3_endpoint)
    if s3_region is not None:
        row.s3_region = (s3_region or "").strip() or None
    if s3_bucket is not None:
        row.s3_bucket = s3_bucket.strip() or None
    if s3_assume_role_arn is not None:
        row.s3_assume_role_arn = s3_assume_role_arn.strip() or None
    if s3_assume_role_external_id is not None:
        row.s3_assume_role_external_id = s3_assume_role_external_id.strip() or None

    if s3_access_key_plain is not None or s3_secret_key_plain is not None:
        ak = (s3_access_key_plain or "").strip() or None
        sk = (s3_secret_key_plain or "").strip() or None
        if (ak is None) ^ (sk is None):
            raise HTTPException(400, detail="s3 access key and secret key must be set together or both omitted")
        fnt = fernet_from_master_key()
        if ak and sk:
            if fnt is None:
                raise HTTPException(400, detail="DEVAULT_STORAGE_CONFIG_MASTER_KEY is required to store static keys")
            row.encrypted_access_key = encrypt_optional(ak, fnt)
            row.encrypted_secret_key = encrypt_optional(sk, fnt)
        else:
            row.encrypted_access_key = None
            row.encrypted_secret_key = None

    validate_profile_fields(
        storage_type=row.storage_type,
        local_root=row.local_root,
        s3_endpoint=row.s3_endpoint,
        s3_bucket=row.s3_bucket,
    )
    if row.storage_type == "s3" and not (row.encrypted_access_key and row.encrypted_secret_key):
        raise HTTPException(400, detail="s3 storage profiles require static access key and secret key")
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


def set_active_profile(db: Session, profile_id: uuid.UUID) -> StorageProfile:
    row = require_profile(db, profile_id)
    db.execute(update(StorageProfile).values(is_active=False))
    row.is_active = True
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


def delete_profile(db: Session, profile_id: uuid.UUID) -> None:
    row = require_profile(db, profile_id)
    if row.is_active:
        raise HTTPException(400, detail="cannot delete the active storage profile; activate another first")
    ref = db.scalar(select(Artifact.id).where(Artifact.storage_profile_id == profile_id).limit(1))
    if ref is not None:
        raise HTTPException(409, detail="storage profile is still referenced by artifacts")
    db.delete(row)
    db.commit()


def profile_out_dict(row: StorageProfile) -> dict[str, object]:
    return {
        "id": row.id,
        "name": row.name,
        "slug": row.slug,
        "storage_type": row.storage_type,
        "is_active": row.is_active,
        "local_root": row.local_root,
        "s3_endpoint": row.s3_endpoint,
        "s3_region": row.s3_region,
        "s3_bucket": row.s3_bucket,
        "has_static_credentials": bool(row.encrypted_access_key and row.encrypted_secret_key),
        "s3_assume_role_arn": row.s3_assume_role_arn,
        "s3_assume_role_external_id": row.s3_assume_role_external_id,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }
