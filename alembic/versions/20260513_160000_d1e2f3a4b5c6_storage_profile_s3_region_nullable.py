"""storage_profiles.s3_region nullable (optional in API)

Revision ID: d1e2f3a4b5c6
Revises: c8d9e0f1a2b3
Create Date: 2026-05-13

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, None] = "c8d9e0f1a2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("ALTER TABLE devault_storage_profiles ALTER COLUMN s3_region DROP DEFAULT"))
    op.execute(sa.text("ALTER TABLE devault_storage_profiles ALTER COLUMN s3_region DROP NOT NULL"))


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE devault_storage_profiles SET s3_region = 'us-east-1' "
            "WHERE s3_region IS NULL OR trim(s3_region) = ''"
        )
    )
    op.execute(sa.text("ALTER TABLE devault_storage_profiles ALTER COLUMN s3_region SET NOT NULL"))
    op.execute(sa.text("ALTER TABLE devault_storage_profiles ALTER COLUMN s3_region SET DEFAULT 'us-east-1'"))
