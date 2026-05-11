"""P2: control-plane API keys and scopes.

Revision ID: p2_001
Revises: p0_001
Create Date: 2026-05-10

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from devault_iam.db.constants import prefixed_fk as pfk
from devault_iam.db.constants import prefixed_table as pt

revision: str = "p2_001"
down_revision: Union[str, None] = "p0_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        pt("api_keys"),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("key_prefix", sa.String(length=64), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("created_by_user_id", sa.UUID(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], [pfk("users", "id")], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], [pfk("tenants", "id")], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_api_keys_tenant_id"), pt("api_keys"), ["tenant_id"], unique=False)
    op.create_index(op.f("ix_api_keys_key_hash"), pt("api_keys"), ["key_hash"], unique=True)

    op.create_table(
        pt("api_key_scopes"),
        sa.Column("api_key_id", sa.UUID(), nullable=False),
        sa.Column("permission_key", sa.String(length=128), nullable=False),
        sa.ForeignKeyConstraint(["api_key_id"], [pfk("api_keys", "id")], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("api_key_id", "permission_key"),
    )


def downgrade() -> None:
    op.drop_table(pt("api_key_scopes"))
    op.drop_index(op.f("ix_api_keys_key_hash"), table_name=pt("api_keys"))
    op.drop_index(op.f("ix_api_keys_tenant_id"), table_name=pt("api_keys"))
    op.drop_table(pt("api_keys"))
