"""policies, schedules, job celery_task_id

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-08

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from devault.db.constants import prefixed_fk as pfk
from devault.db.constants import prefixed_table as pt

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        pt("policies"),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("plugin", sa.String(length=32), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_policies_plugin"), pt("policies"), ["plugin"], unique=False)

    op.create_table(
        pt("schedules"),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("policy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cron_expression", sa.String(length=128), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="UTC"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["policy_id"], [pfk("policies", "id")], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_schedules_policy_id"), pt("schedules"), ["policy_id"], unique=False)

    op.add_column(pt("jobs"), sa.Column("celery_task_id", sa.String(length=128), nullable=True))
    op.create_foreign_key(
        "fk_jobs_policy_id_policies",
        pt("jobs"),
        pt("policies"),
        ["policy_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_jobs_policy_id_policies", pt("jobs"), type_="foreignkey")
    op.drop_column(pt("jobs"), "celery_task_id")
    op.drop_index(op.f("ix_schedules_policy_id"), table_name=pt("schedules"))
    op.drop_table(pt("schedules"))
    op.drop_index(op.f("ix_policies_plugin"), table_name=pt("policies"))
    op.drop_table(pt("policies"))
