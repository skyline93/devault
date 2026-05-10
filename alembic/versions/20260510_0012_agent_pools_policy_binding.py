"""agent_pools + members; policies bound_agent_id / bound_agent_pool_id (§十四 05–07)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_pools",
        sa.Column("id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_pools_tenant_id", "agent_pools", ["tenant_id"], unique=False)

    op.create_table(
        "agent_pool_members",
        sa.Column("pool_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["pool_id"], ["agent_pools.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("pool_id", "agent_id"),
    )

    op.add_column("policies", sa.Column("bound_agent_id", sa.UUID(as_uuid=True), nullable=True))
    op.add_column("policies", sa.Column("bound_agent_pool_id", sa.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_policies_bound_agent_pool_id",
        "policies",
        "agent_pools",
        ["bound_agent_pool_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        "ck_policies_execution_binding_exclusive",
        "policies",
        "NOT (bound_agent_id IS NOT NULL AND bound_agent_pool_id IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_policies_execution_binding_exclusive", "policies", type_="check")
    op.drop_constraint("fk_policies_bound_agent_pool_id", "policies", type_="foreignkey")
    op.drop_column("policies", "bound_agent_pool_id")
    op.drop_column("policies", "bound_agent_id")
    op.drop_table("agent_pool_members")
    op.drop_index("ix_agent_pools_tenant_id", table_name="agent_pools")
    op.drop_table("agent_pools")
