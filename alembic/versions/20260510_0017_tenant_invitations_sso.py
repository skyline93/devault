"""§十六 P2: tenant invitations + per-tenant OIDC/SAML metadata fields."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenant_invitations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column(
            "invited_by_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("console_users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_tenant_invitations_tenant_pending_email",
        "tenant_invitations",
        ["tenant_id", "email"],
    )

    op.add_column("tenants", sa.Column("sso_oidc_issuer", sa.Text(), nullable=True))
    op.add_column("tenants", sa.Column("sso_oidc_audience", sa.Text(), nullable=True))
    op.add_column(
        "tenants",
        sa.Column("sso_oidc_role_claim", sa.String(length=64), nullable=False, server_default="devault_role"),
    )
    op.add_column(
        "tenants",
        sa.Column("sso_oidc_email_claim", sa.String(length=64), nullable=False, server_default="email"),
    )
    op.add_column(
        "tenants",
        sa.Column("sso_password_login_disabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "tenants",
        sa.Column("sso_jit_provisioning", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("tenants", sa.Column("sso_saml_entity_id", sa.Text(), nullable=True))
    op.add_column("tenants", sa.Column("sso_saml_acs_url", sa.Text(), nullable=True))
    op.create_index(
        "uq_tenants_oidc_issuer_audience",
        "tenants",
        ["sso_oidc_issuer", "sso_oidc_audience"],
        unique=True,
        postgresql_where=sa.text("sso_oidc_issuer IS NOT NULL AND sso_oidc_audience IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_tenants_oidc_issuer_audience", table_name="tenants")
    op.drop_column("tenants", "sso_saml_acs_url")
    op.drop_column("tenants", "sso_saml_entity_id")
    op.drop_column("tenants", "sso_jit_provisioning")
    op.drop_column("tenants", "sso_password_login_disabled")
    op.drop_column("tenants", "sso_oidc_email_claim")
    op.drop_column("tenants", "sso_oidc_role_claim")
    op.drop_column("tenants", "sso_oidc_audience")
    op.drop_column("tenants", "sso_oidc_issuer")
    op.drop_index("ix_tenant_invitations_tenant_pending_email", table_name="tenant_invitations")
    op.drop_table("tenant_invitations")
