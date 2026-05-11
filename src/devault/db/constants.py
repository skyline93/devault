"""Shared database constants (e.g. migration seed IDs)."""

from __future__ import annotations

import uuid

# Physical PostgreSQL table names are ``{TABLE_PREFIX}_{logical}`` (single underscore).
# Change only here (and matching Alembic revisions) to rename the whole control-plane schema.
TABLE_PREFIX = "devault"


def prefixed_table(logical_name: str) -> str:
    """Resolve a logical table name to the physical name (used by ORM base and migrations)."""

    return f"{TABLE_PREFIX}_{logical_name}"


def prefixed_fk(logical_table: str, column: str) -> str:
    """ForeignKey / FKConstraint target string ``{prefixed_table}.{column}``."""

    return f"{prefixed_table(logical_table)}.{column}"


# Seeded by Alembic revision 0005; all legacy rows attach to this tenant.
DEFAULT_TENANT_UUID = uuid.UUID("00000000-0000-0000-0000-000000000001")
