"""Remove legacy console auth tables; HTTP control plane uses IAM JWT only."""

from __future__ import annotations

from alembic import op

from devault.db.constants import prefixed_table as pt

# Distinct id: another migration already uses revision "0012" (agent_pools).
# Must run **after** 0017 so console/legacy tables created in 0015–0017 exist before DROP.
revision = "0012_drop_legacy"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(f"DROP TABLE IF EXISTS {pt('tenant_invitations')} CASCADE")
    op.execute(f"DROP TABLE IF EXISTS {pt('password_reset_tokens')} CASCADE")
    op.execute(f"DROP TABLE IF EXISTS {pt('tenant_memberships')} CASCADE")
    op.execute(f"DROP TABLE IF EXISTS {pt('console_users')} CASCADE")
    op.execute(f"DROP TABLE IF EXISTS {pt('control_plane_api_keys')} CASCADE")


def downgrade() -> None:
    raise NotImplementedError("legacy auth tables are not recreated")
