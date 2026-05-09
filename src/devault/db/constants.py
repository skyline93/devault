"""Shared database constants (e.g. migration seed IDs)."""

from __future__ import annotations

import uuid

# Seeded by Alembic revision 0005; all legacy rows attach to this tenant.
DEFAULT_TENANT_UUID = uuid.UUID("00000000-0000-0000-0000-000000000001")
