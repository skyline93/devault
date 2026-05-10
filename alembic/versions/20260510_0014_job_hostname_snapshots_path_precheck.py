"""Job lease/completed hostname snapshots (§十四-12); supports path_precheck jobs (§十四-11)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("lease_agent_hostname", sa.String(length=255), nullable=True))
    op.add_column("jobs", sa.Column("completed_agent_hostname", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "completed_agent_hostname")
    op.drop_column("jobs", "lease_agent_hostname")
