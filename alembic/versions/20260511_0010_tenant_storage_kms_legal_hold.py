"""tenant BYOB/KMS flags, artifact legal hold

Revision ID: 0010
Revises: 0009
Create Date: 2026-05-11
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from devault.db.constants import prefixed_table as pt

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        pt("tenants"),
        sa.Column("require_encrypted_artifacts", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(pt("tenants"), sa.Column("kms_envelope_key_id", sa.String(length=2048), nullable=True))
    op.add_column(pt("tenants"), sa.Column("s3_bucket", sa.String(length=255), nullable=True))
    op.add_column(pt("tenants"), sa.Column("s3_assume_role_arn", sa.String(length=2048), nullable=True))
    op.add_column(pt("tenants"), sa.Column("s3_assume_role_external_id", sa.String(length=1224), nullable=True))

    op.add_column(
        pt("artifacts"),
        sa.Column("legal_hold", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index(
        "ix_artifacts_legal_hold",
        pt("artifacts"),
        ["legal_hold"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_artifacts_legal_hold", table_name=pt("artifacts"))
    op.drop_column(pt("artifacts"), "legal_hold")
    op.drop_column(pt("tenants"), "s3_assume_role_external_id")
    op.drop_column(pt("tenants"), "s3_assume_role_arn")
    op.drop_column(pt("tenants"), "s3_bucket")
    op.drop_column(pt("tenants"), "kms_envelope_key_id")
    op.drop_column(pt("tenants"), "require_encrypted_artifacts")
