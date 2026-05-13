"""storage_profiles + artifact storage_profile_id; drop tenant BYOB columns

Revision ID: c8d9e0f1a2b3
Revises: a1b2c3d4e5f6
Create Date: 2026-05-13

No seed row: create profiles via control plane (e.g. console). Existing artifacts keep
``storage_profile_id`` NULL until backfilled; runtime resolves NULL to the active profile
for read/retention where appropriate.

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c8d9e0f1a2b3"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "devault_storage_profiles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("storage_type", sa.String(length=16), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("local_root", sa.Text(), nullable=True),
        sa.Column("s3_endpoint", sa.Text(), nullable=True),
        sa.Column("s3_region", sa.String(length=64), nullable=False, server_default="us-east-1"),
        sa.Column("s3_bucket", sa.String(length=255), nullable=True),
        sa.Column("s3_use_ssl", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("encrypted_access_key", sa.Text(), nullable=True),
        sa.Column("encrypted_secret_key", sa.Text(), nullable=True),
        sa.Column("s3_assume_role_arn", sa.Text(), nullable=True),
        sa.Column("s3_assume_role_external_id", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_devault_storage_profiles_slug", "devault_storage_profiles", ["slug"], unique=True)
    op.execute(
        sa.text(
            "CREATE UNIQUE INDEX devault_storage_profiles_one_active "
            "ON devault_storage_profiles ((1)) WHERE is_active"
        )
    )

    op.add_column(
        "devault_artifacts",
        sa.Column("storage_profile_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "devault_artifacts_storage_profile_id_fkey",
        "devault_artifacts",
        "devault_storage_profiles",
        ["storage_profile_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_devault_artifacts_storage_profile_id",
        "devault_artifacts",
        ["storage_profile_id"],
        unique=False,
    )

    op.drop_column("devault_tenants", "s3_bucket")
    op.drop_column("devault_tenants", "s3_assume_role_arn")
    op.drop_column("devault_tenants", "s3_assume_role_external_id")


def downgrade() -> None:
    op.add_column(
        "devault_tenants",
        sa.Column("s3_bucket", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "devault_tenants",
        sa.Column("s3_assume_role_arn", sa.String(length=2048), nullable=True),
    )
    op.add_column(
        "devault_tenants",
        sa.Column("s3_assume_role_external_id", sa.String(length=1224), nullable=True),
    )

    op.drop_index("ix_devault_artifacts_storage_profile_id", table_name="devault_artifacts")
    op.drop_constraint("devault_artifacts_storage_profile_id_fkey", "devault_artifacts", type_="foreignkey")
    op.drop_column("devault_artifacts", "storage_profile_id")

    op.execute(sa.text("DROP INDEX IF EXISTS devault_storage_profiles_one_active"))
    op.drop_index("ix_devault_storage_profiles_slug", table_name="devault_storage_profiles")
    op.drop_table("devault_storage_profiles")
