"""Add WIP multipart columns on jobs for cross-restart resume."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from devault.db.constants import prefixed_table as pt

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        pt("jobs"),
        sa.Column("bundle_wip_multipart_upload_id", sa.String(length=1024), nullable=True),
    )
    op.add_column(
        pt("jobs"),
        sa.Column("bundle_wip_content_length", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        pt("jobs"),
        sa.Column("bundle_wip_part_size_bytes", sa.BigInteger(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column(pt("jobs"), "bundle_wip_part_size_bytes")
    op.drop_column(pt("jobs"), "bundle_wip_content_length")
    op.drop_column(pt("jobs"), "bundle_wip_multipart_upload_id")
