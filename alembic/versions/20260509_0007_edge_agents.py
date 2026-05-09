"""edge_agents: Agent fleet registry from Heartbeat/Register

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-09

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "edge_agents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("agent_release", sa.String(length=64), nullable=True),
        sa.Column("proto_package", sa.String(length=128), nullable=True),
        sa.Column("git_commit", sa.String(length=64), nullable=True),
        sa.Column("last_register_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_edge_agents_last_seen_at",
        "edge_agents",
        ["last_seen_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_edge_agents_last_seen_at", table_name="edge_agents")
    op.drop_table("edge_agents")
