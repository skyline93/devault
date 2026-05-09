"""Purge expired artifacts (metadata + storage objects)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select

from devault.db.models import Artifact
from devault.db.session import SessionLocal
from devault.observability.metrics import RETENTION_PURGED_TOTAL, RETENTION_PURGE_ERRORS_TOTAL
from devault.settings import Settings
from devault.storage import get_storage

logger = logging.getLogger(__name__)

_BATCH = 50


def purge_expired_artifacts(settings: Settings) -> tuple[int, int]:
    """Delete artifacts whose ``retain_until`` is in the past: objects first, then DB row.

    Returns ``(purged_count, error_count)``.
    """
    if not settings.retention_cleanup_enabled:
        return 0, 0

    now = datetime.now(timezone.utc)
    storage = get_storage(settings)
    purged = 0
    errors = 0

    while True:
        db = SessionLocal()
        try:
            stmt = (
                select(Artifact)
                .where(
                    Artifact.retain_until.is_not(None),
                    Artifact.retain_until < now,
                )
                .limit(_BATCH)
                .order_by(Artifact.retain_until.asc())
            )
            bind = db.get_bind()
            if bind.dialect.name == "postgresql":
                stmt = stmt.with_for_update(skip_locked=True)

            rows = list(db.scalars(stmt).all())
        finally:
            db.close()

        if not rows:
            break

        for art in rows:
            tid = str(art.tenant_id)
            db_one = SessionLocal()
            try:
                fresh = db_one.get(Artifact, art.id)
                if fresh is None:
                    continue
                storage.delete_object(fresh.bundle_key)
                storage.delete_object(fresh.manifest_key)
                db_one.delete(fresh)
                db_one.commit()
                purged += 1
                RETENTION_PURGED_TOTAL.labels(tenant_id=tid).inc()
                logger.info(
                    "retention purge artifact_id=%s tenant_id=%s retain_until=%s",
                    fresh.id,
                    tid,
                    fresh.retain_until,
                )
            except Exception:
                errors += 1
                db_one.rollback()
                RETENTION_PURGE_ERRORS_TOTAL.inc()
                logger.exception(
                    "retention purge failed artifact_id=%s bundle_key=%s",
                    getattr(art, "id", None),
                    getattr(art, "bundle_key", None),
                )
            finally:
                db_one.close()

        if len(rows) < _BATCH:
            break

    return purged, errors
