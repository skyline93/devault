"""agent_tokens_refactor

Revision ID: a1b2c3d4e5f6
Revises: 9d455b3193d4
Create Date: 2026-05-12 12:15:00

Greenfield cutover: drop enrollment and agent pools; add tenant agent tokens.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "9d455b3193d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("devault_agent_pool_members")

    op.drop_constraint(
        "devault_policies_bound_agent_pool_id_fkey",
        "devault_policies",
        type_="foreignkey",
    )
    op.drop_column("devault_policies", "bound_agent_pool_id")

    op.drop_index(op.f("ix_devault_agent_pools_tenant_id"), table_name="devault_agent_pools")
    op.drop_table("devault_agent_pools")
    op.drop_table("devault_agent_enrollments")

    op.create_table(
        "devault_agent_tokens",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["devault_tenants.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(op.f("ix_devault_agent_tokens_tenant_id"), "devault_agent_tokens", ["tenant_id"], unique=False)

    op.add_column("devault_edge_agents", sa.Column("agent_token_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "devault_edge_agents_agent_token_id_fkey",
        "devault_edge_agents",
        "devault_agent_tokens",
        ["agent_token_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        op.f("ix_devault_edge_agents_agent_token_id"),
        "devault_edge_agents",
        ["agent_token_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_devault_edge_agents_agent_token_id"), table_name="devault_edge_agents")
    op.drop_constraint("devault_edge_agents_agent_token_id_fkey", "devault_edge_agents", type_="foreignkey")
    op.drop_column("devault_edge_agents", "agent_token_id")

    op.drop_index(op.f("ix_devault_agent_tokens_tenant_id"), table_name="devault_agent_tokens")
    op.drop_table("devault_agent_tokens")

    op.create_table(
        "devault_agent_enrollments",
        sa.Column("agent_id", sa.UUID(), nullable=False),
        sa.Column("allowed_tenant_ids", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("agent_id"),
    )
    op.create_table(
        "devault_agent_pools",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["devault_tenants.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_devault_agent_pools_tenant_id"), "devault_agent_pools", ["tenant_id"], unique=False)
    op.create_table(
        "devault_agent_pool_members",
        sa.Column("pool_id", sa.UUID(), nullable=False),
        sa.Column("agent_id", sa.UUID(), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["pool_id"], ["devault_agent_pools.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("pool_id", "agent_id"),
    )

    op.add_column("devault_policies", sa.Column("bound_agent_pool_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "devault_policies_bound_agent_pool_id_fkey",
        "devault_policies",
        "devault_agent_pools",
        ["bound_agent_pool_id"],
        ["id"],
        ondelete="SET NULL",
    )
