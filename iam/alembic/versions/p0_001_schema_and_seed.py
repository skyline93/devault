"""P0: IAM core schema + RBAC seed + default tenant.

Revision ID: p0_001
Revises:
Create Date: 2026-05-10

"""

from __future__ import annotations

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "p0_001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NS = uuid.UUID("018f0000-0000-7000-8000-000000000001")


def _nid(s: str) -> str:
    return str(uuid.uuid5(_NS, s))


def upgrade() -> None:
    op.create_table(
        "users",
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
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_status"), "users", ["status"], unique=False)

    op.create_table(
        "tenants",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("plan", sa.String(length=64), nullable=False, server_default="standard"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("owner_user_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tenants_slug"), "tenants", ["slug"], unique=True)
    op.create_index(op.f("ix_tenants_status"), "tenants", ["status"], unique=False)

    op.create_table(
        "permissions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("description", sa.String(length=512), nullable=False, server_default=""),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_permissions_key"), "permissions", ["key"], unique=True)

    op.create_table(
        "roles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_roles_tenant_id"), "roles", ["tenant_id"], unique=False)
    op.create_index(
        "uq_roles_name_global",
        "roles",
        ["name"],
        unique=True,
        postgresql_where=sa.text("tenant_id IS NULL"),
    )
    op.create_index(
        "uq_roles_tenant_name_nn",
        "roles",
        ["tenant_id", "name"],
        unique=True,
        postgresql_where=sa.text("tenant_id IS NOT NULL"),
    )

    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.UUID(), nullable=False),
        sa.Column("permission_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
    )

    op.create_table(
        "tenant_members",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("role_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "user_id", name="uq_tenant_members_tenant_user"),
    )
    op.create_index(op.f("ix_tenant_members_role_id"), "tenant_members", ["role_id"], unique=False)
    op.create_index(op.f("ix_tenant_members_status"), "tenant_members", ["status"], unique=False)
    op.create_index(op.f("ix_tenant_members_tenant_id"), "tenant_members", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_tenant_members_user_id"), "tenant_members", ["user_id"], unique=False)

    op.create_table(
        "sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=64), nullable=False),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sessions_refresh_token_hash"), "sessions", ["refresh_token_hash"], unique=True)
    op.create_index(op.f("ix_sessions_user_id"), "sessions", ["user_id"], unique=False)

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
        "permissions",
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
        "roles",
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
        "role_permissions",
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

    tenant_default_id = _nid("tenant.default")
    tenants_t = sa.table(
        "tenants",
        sa.column("id", sa.UUID()),
        sa.column("name", sa.String()),
        sa.column("slug", sa.String()),
        sa.column("plan", sa.String()),
        sa.column("status", sa.String()),
        sa.column("owner_user_id", sa.UUID()),
    )
    op.bulk_insert(
        tenants_t,
        [
            {
                "id": tenant_default_id,
                "name": "Default",
                "slug": "default",
                "plan": "standard",
                "status": "active",
                "owner_user_id": None,
            }
        ],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_sessions_user_id"), table_name="sessions")
    op.drop_index(op.f("ix_sessions_refresh_token_hash"), table_name="sessions")
    op.drop_table("sessions")
    op.drop_index(op.f("ix_tenant_members_user_id"), table_name="tenant_members")
    op.drop_index(op.f("ix_tenant_members_tenant_id"), table_name="tenant_members")
    op.drop_index(op.f("ix_tenant_members_status"), table_name="tenant_members")
    op.drop_index(op.f("ix_tenant_members_role_id"), table_name="tenant_members")
    op.drop_table("tenant_members")
    op.drop_table("role_permissions")
    op.drop_index("uq_roles_tenant_name_nn", table_name="roles")
    op.drop_index("uq_roles_name_global", table_name="roles")
    op.drop_index(op.f("ix_roles_tenant_id"), table_name="roles")
    op.drop_table("roles")
    op.drop_index(op.f("ix_permissions_key"), table_name="permissions")
    op.drop_table("permissions")
    op.drop_index(op.f("ix_tenants_status"), table_name="tenants")
    op.drop_index(op.f("ix_tenants_slug"), table_name="tenants")
    op.drop_table("tenants")
    op.drop_index(op.f("ix_users_status"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
