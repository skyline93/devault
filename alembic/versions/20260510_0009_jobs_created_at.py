"""jobs.created_at for ordering and UI

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-10
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from devault.db.constants import prefixed_table as pt

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(pt("jobs"), sa.Column("created_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(sa.text(f"UPDATE {pt('jobs')} SET created_at = COALESCE(finished_at, started_at, NOW())"))
    op.alter_column(
        pt("jobs"),
        "created_at",
        nullable=False,
        server_default=sa.text("now()"),
    )


def downgrade() -> None:
    op.drop_column(pt("jobs"), "created_at")
