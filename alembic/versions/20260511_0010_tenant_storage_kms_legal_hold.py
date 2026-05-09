"""tenant BYOB/KMS flags, artifact legal hold

Revision ID: 0010
Revises: 0009
Create Date: 2026-05-11
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("require_encrypted_artifacts", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("tenants", sa.Column("kms_envelope_key_id", sa.String(length=2048), nullable=True))
    op.add_column("tenants", sa.Column("s3_bucket", sa.String(length=255), nullable=True))
    op.add_column("tenants", sa.Column("s3_assume_role_arn", sa.String(length=2048), nullable=True))
    op.add_column("tenants", sa.Column("s3_assume_role_external_id", sa.String(length=1224), nullable=True))

    op.add_column(
        "artifacts",
        sa.Column("legal_hold", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index(
        "ix_artifacts_legal_hold",
        "artifacts",
        ["legal_hold"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_artifacts_legal_hold", table_name="artifacts")
    op.drop_column("artifacts", "legal_hold")
    op.drop_column("tenants", "s3_assume_role_external_id")
    op.drop_column("tenants", "s3_assume_role_arn")
    op.drop_column("tenants", "s3_bucket")
    op.drop_column("tenants", "kms_envelope_key_id")
    op.drop_column("tenants", "require_encrypted_artifacts")
