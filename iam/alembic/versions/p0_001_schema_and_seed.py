"""P0: IAM core schema + RBAC seed (no default tenant).

Revision ID: p0_001
Revises:
Create Date: 2026-05-10

"""

from __future__ import annotations

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from devault_iam.db.constants import prefixed_fk as pfk
from devault_iam.db.constants import prefixed_table as pt

revision: str = "p0_001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NS = uuid.UUID("018f0000-0000-7000-8000-000000000001")


def _nid(s: str) -> str:
    return str(uuid.uuid5(_NS, s))


def upgrade() -> None:
    op.create_table(
        pt("users"),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("totp_secret", sa.Text(), nullable=True),
        sa.Column("totp_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), pt("users"), ["email"], unique=True)
    op.create_index(op.f("ix_users_status"), pt("users"), ["status"], unique=False)

    op.create_table(
        pt("tenants"),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("plan", sa.String(length=64), nullable=False, server_default="standard"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("owner_user_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], [pfk("users", "id")], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tenants_slug"), pt("tenants"), ["slug"], unique=True)
    op.create_index(op.f("ix_tenants_status"), pt("tenants"), ["status"], unique=False)

    op.create_table(
        pt("permissions"),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("description", sa.String(length=512), nullable=False, server_default=""),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_permissions_key"), pt("permissions"), ["key"], unique=True)

    op.create_table(
        pt("roles"),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.ForeignKeyConstraint(["tenant_id"], [pfk("tenants", "id")], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_roles_tenant_id"), pt("roles"), ["tenant_id"], unique=False)
    op.create_index(
        "uq_roles_name_global",
        pt("roles"),
        ["name"],
        unique=True,
        postgresql_where=sa.text("tenant_id IS NULL"),
    )
    op.create_index(
        "uq_roles_tenant_name_nn",
        pt("roles"),
        ["tenant_id", "name"],
        unique=True,
        postgresql_where=sa.text("tenant_id IS NOT NULL"),
    )

    op.create_table(
        pt("role_permissions"),
        sa.Column("role_id", sa.UUID(), nullable=False),
        sa.Column("permission_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["permission_id"], [pfk("permissions", "id")], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], [pfk("roles", "id")], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
    )

    op.create_table(
        pt("tenant_members"),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("role_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], [pfk("roles", "id")], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], [pfk("tenants", "id")], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], [pfk("users", "id")], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "user_id", name="uq_tenant_members_tenant_user"),
    )
    op.create_index(op.f("ix_tenant_members_role_id"), pt("tenant_members"), ["role_id"], unique=False)
    op.create_index(op.f("ix_tenant_members_status"), pt("tenant_members"), ["status"], unique=False)
    op.create_index(op.f("ix_tenant_members_tenant_id"), pt("tenant_members"), ["tenant_id"], unique=False)
    op.create_index(op.f("ix_tenant_members_user_id"), pt("tenant_members"), ["user_id"], unique=False)

    op.create_table(
        pt("sessions"),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=64), nullable=False),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], [pfk("users", "id")], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sessions_refresh_token_hash"), pt("sessions"), ["refresh_token_hash"], unique=True)
    op.create_index(op.f("ix_sessions_user_id"), pt("sessions"), ["user_id"], unique=False)

    # --- Seed permissions (stable UUIDs) ---
    p_console_read = _nid("perm.devault.console.read")
    p_console_write = _nid("perm.devault.console.write")
    p_console_admin = _nid("perm.devault.console.admin")
    p_control_read = _nid("perm.devault.control.read")
    p_control_write = _nid("perm.devault.control.write")
    p_platform_admin = _nid("perm.devault.platform.admin")

    perm_rows = [
        (p_console_read, "devault.console.read", "Read console and tenant-scoped control-plane data"),
        (p_console_write, "devault.console.write", "Write console operations (non-admin)"),
        (p_console_admin, "devault.console.admin", "Tenant administration (members, settings)"),
        (p_control_read, "devault.control.read", "Read backup control resources"),
        (p_control_write, "devault.control.write", "Create/update backup control resources"),
        (p_platform_admin, "devault.platform.admin", "Cross-tenant platform administration"),
    ]
    permissions_t = sa.table(
        pt("permissions"),
        sa.column("id", sa.UUID()),
        sa.column("key", sa.String()),
        sa.column("description", sa.String()),
    )
    op.bulk_insert(
        permissions_t,
        [{"id": r[0], "key": r[1], "description": r[2]} for r in perm_rows],
    )

    r_tenant_admin = _nid("role.tenant_admin")
    r_operator = _nid("role.operator")
    r_auditor = _nid("role.auditor")
    r_platform_admin = _nid("role.platform_admin")

    roles_t = sa.table(
        pt("roles"),
        sa.column("id", sa.UUID()),
        sa.column("tenant_id", sa.UUID()),
        sa.column("name", sa.String()),
        sa.column("is_system", sa.Boolean()),
    )
    op.bulk_insert(
        roles_t,
        [
            {
                "id": r_tenant_admin,
                "tenant_id": None,
                "name": "tenant_admin",
                "is_system": True,
            },
            {"id": r_operator, "tenant_id": None, "name": "operator", "is_system": True},
            {"id": r_auditor, "tenant_id": None, "name": "auditor", "is_system": True},
            {
                "id": r_platform_admin,
                "tenant_id": None,
                "name": "platform_admin",
                "is_system": True,
            },
        ],
    )

    rp = sa.table(
        pt("role_permissions"),
        sa.column("role_id", sa.UUID()),
        sa.column("permission_id", sa.UUID()),
    )

    def rp_rows(role: str, perm_ids: list[str]) -> list[dict[str, str]]:
        rid = {
            "tenant_admin": r_tenant_admin,
            "operator": r_operator,
            "auditor": r_auditor,
            "platform_admin": r_platform_admin,
        }[role]
        return [{"role_id": rid, "permission_id": pid} for pid in perm_ids]

    all_perms = [
        p_console_read,
        p_console_write,
        p_console_admin,
        p_control_read,
        p_control_write,
    ]
    op.bulk_insert(rp, rp_rows("tenant_admin", all_perms))
    op.bulk_insert(
        rp,
        rp_rows(
            "operator",
            [p_console_read, p_console_write, p_control_read, p_control_write],
        ),
    )
    op.bulk_insert(rp, rp_rows("auditor", [p_console_read, p_control_read]))
    op.bulk_insert(
        rp,
        rp_rows("platform_admin", all_perms + [p_platform_admin]),
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_sessions_user_id"), table_name=pt("sessions"))
    op.drop_index(op.f("ix_sessions_refresh_token_hash"), table_name=pt("sessions"))
    op.drop_table(pt("sessions"))
    op.drop_index(op.f("ix_tenant_members_user_id"), table_name=pt("tenant_members"))
    op.drop_index(op.f("ix_tenant_members_tenant_id"), table_name=pt("tenant_members"))
    op.drop_index(op.f("ix_tenant_members_status"), table_name=pt("tenant_members"))
    op.drop_index(op.f("ix_tenant_members_role_id"), table_name=pt("tenant_members"))
    op.drop_table(pt("tenant_members"))
    op.drop_table(pt("role_permissions"))
    op.drop_index("uq_roles_tenant_name_nn", table_name=pt("roles"))
    op.drop_index("uq_roles_name_global", table_name=pt("roles"))
    op.drop_index(op.f("ix_roles_tenant_id"), table_name=pt("roles"))
    op.drop_table(pt("roles"))
    op.drop_index(op.f("ix_permissions_key"), table_name=pt("permissions"))
    op.drop_table(pt("permissions"))
    op.drop_index(op.f("ix_tenants_status"), table_name=pt("tenants"))
    op.drop_index(op.f("ix_tenants_slug"), table_name=pt("tenants"))
    op.drop_table(pt("tenants"))
    op.drop_index(op.f("ix_users_status"), table_name=pt("users"))
    op.drop_index(op.f("ix_users_email"), table_name=pt("users"))
    op.drop_table(pt("users"))
