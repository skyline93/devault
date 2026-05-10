"""Edge Agent Heartbeat snapshot + tenant policy_paths_allowlist_mode (§十四 08, 10)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("edge_agents", sa.Column("hostname", sa.String(length=255), nullable=True))
    op.add_column("edge_agents", sa.Column("host_os", sa.String(length=255), nullable=True))
    op.add_column("edge_agents", sa.Column("region", sa.String(length=128), nullable=True))
    op.add_column("edge_agents", sa.Column("agent_env", sa.String(length=128), nullable=True))
    op.add_column(
        "edge_agents",
        sa.Column("backup_path_allowlist", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "tenants",
        sa.Column(
            "policy_paths_allowlist_mode",
            sa.String(length=16),
            nullable=False,
            server_default="off",
        ),
    )


def downgrade() -> None:
    op.drop_column("tenants", "policy_paths_allowlist_mode")
    op.drop_column("edge_agents", "backup_path_allowlist")
    op.drop_column("edge_agents", "agent_env")
    op.drop_column("edge_agents", "region")
    op.drop_column("edge_agents", "host_os")
    op.drop_column("edge_agents", "hostname")
