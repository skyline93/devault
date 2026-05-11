"""agent lease fields, drop celery_task_id

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-08

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

from devault.db.constants import prefixed_table as pt

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        pt("jobs"),
        sa.Column("lease_agent_id", UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        pt("jobs"),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.drop_column(pt("jobs"), "celery_task_id")


def downgrade() -> None:
    op.add_column(
        pt("jobs"),
        sa.Column("celery_task_id", sa.String(length=128), nullable=True),
    )
    op.drop_column(pt("jobs"), "lease_expires_at")
    op.drop_column(pt("jobs"), "lease_agent_id")
