"""§十六 P0: console users (email + password hash) and tenant memberships (RBAC per tenant)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

from devault.db.constants import prefixed_fk as pfk
from devault.db.constants import prefixed_table as pt

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        pt("console_users"),
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("disabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("email", name="uq_console_users_email"),
    )
    op.create_index("ix_console_users_email", pt("console_users"), ["email"], unique=True)

    op.create_table(
        pt("tenant_memberships"),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey(pfk("console_users", "id"), ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey(pfk("tenants", "id"), ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("user_id", "tenant_id", name="pk_tenant_memberships"),
    )
    op.create_index("ix_tenant_memberships_tenant_id", pt("tenant_memberships"), ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_tenant_memberships_tenant_id", table_name=pt("tenant_memberships"))
    op.drop_table(pt("tenant_memberships"))
    op.drop_index("ix_console_users_email", table_name=pt("console_users"))
    op.drop_table(pt("console_users"))
