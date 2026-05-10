"""agent_enrollments: Agent UUID -> allowed tenant IDs for Register + LeaseJobs isolation."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

# Compose demo: fixed agent id (see deploy/docker-compose.yml DEVAULT_AGENT_ID).
_DEMO_AGENT_ID = "00000000-0000-4000-8000-000000000001"


def upgrade() -> None:
    op.create_table(
        "agent_enrollments",
        sa.Column("agent_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("allowed_tenant_ids", JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("agent_id", name="pk_agent_enrollments"),
    )
    op.get_bind().execute(
        text(
            """
            INSERT INTO agent_enrollments (agent_id, allowed_tenant_ids, created_at, updated_at)
            SELECT CAST(:demo_agent AS uuid),
                   jsonb_build_array(t.id::text),
                   now(),
                   now()
            FROM tenants t
            WHERE t.slug = 'default'
            LIMIT 1
            """,
        ),
        {"demo_agent": _DEMO_AGENT_ID},
    )


def downgrade() -> None:
    op.drop_table("agent_enrollments")
