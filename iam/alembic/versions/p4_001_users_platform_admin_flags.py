"""P4: platform admin user flag + optional must_change_password.

Revision ID: p4_001
Revises: p3_001
Create Date: 2026-05-11

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from devault_iam.db.constants import prefixed_table as pt

revision: str = "p4_001"
down_revision: Union[str, None] = "p3_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        pt("users"),
        sa.Column("is_platform_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        pt("users"),
        sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.alter_column(pt("users"), "is_platform_admin", server_default=None)
    op.alter_column(pt("users"), "must_change_password", server_default=None)


def downgrade() -> None:
    op.drop_column(pt("users"), "must_change_password")
    op.drop_column(pt("users"), "is_platform_admin")
