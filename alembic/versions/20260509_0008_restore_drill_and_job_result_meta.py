"""restore drill schedules + job result_meta

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-09
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

from devault.db.constants import prefixed_fk as pfk
from devault.db.constants import prefixed_table as pt

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        pt("restore_drill_schedules"),
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey(pfk("tenants", "id"), ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "artifact_id",
            UUID(as_uuid=True),
            sa.ForeignKey(pfk("artifacts", "id"), ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("cron_expression", sa.String(128), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="UTC"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("drill_base_path", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.add_column(pt("jobs"), sa.Column("result_meta", JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column(pt("jobs"), "result_meta")
    op.drop_table(pt("restore_drill_schedules"))
