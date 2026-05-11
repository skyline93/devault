"""§十六 P1: tenant MFA flag, console user TOTP, password reset tokens."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

from devault.db.constants import prefixed_fk as pfk
from devault.db.constants import prefixed_table as pt

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        pt("tenants"),
        sa.Column("require_mfa_for_admins", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(pt("console_users"), sa.Column("totp_secret", sa.Text(), nullable=True))
    op.add_column(
        pt("console_users"),
        sa.Column("totp_confirmed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        pt("password_reset_tokens"),
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey(pfk("console_users", "id"), ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("token_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table(pt("password_reset_tokens"))
    op.drop_column(pt("console_users"), "totp_confirmed_at")
    op.drop_column(pt("console_users"), "totp_secret")
    op.drop_column(pt("tenants"), "require_mfa_for_admins")
