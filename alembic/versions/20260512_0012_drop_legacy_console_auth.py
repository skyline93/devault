"""Remove legacy console auth tables; HTTP control plane uses IAM JWT only."""

from __future__ import annotations

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tenant_invitations CASCADE")
    op.execute("DROP TABLE IF EXISTS password_reset_tokens CASCADE")
    op.execute("DROP TABLE IF EXISTS tenant_memberships CASCADE")
    op.execute("DROP TABLE IF EXISTS console_users CASCADE")
    op.execute("DROP TABLE IF EXISTS control_plane_api_keys CASCADE")


def downgrade() -> None:
    raise NotImplementedError("legacy auth tables are not recreated")
