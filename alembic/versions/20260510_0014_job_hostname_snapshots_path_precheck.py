from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from devault.db.constants import prefixed_table as pt

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(pt("jobs"), sa.Column("lease_agent_hostname", sa.String(length=255), nullable=True))
    op.add_column(pt("jobs"), sa.Column("completed_agent_hostname", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column(pt("jobs"), "completed_agent_hostname")
    op.drop_column(pt("jobs"), "lease_agent_hostname")
