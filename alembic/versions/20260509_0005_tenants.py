"""Tenants table; tenant_id on policies, jobs, schedules, artifacts; S3 key isolation."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from devault.db.constants import prefixed_table as pt

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

_DEFAULT_TENANT = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    op.create_table(
        pt("tenants"),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    op.execute(
        sa.text(
            f"INSERT INTO {pt('tenants')} (id, name, slug) VALUES "
            f"('{_DEFAULT_TENANT}'::uuid, 'Default', 'default')"
        )
    )

    op.add_column(
        pt("policies"),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute(sa.text(f"UPDATE {pt('policies')} SET tenant_id = '{_DEFAULT_TENANT}'::uuid"))
    op.alter_column(pt("policies"), "tenant_id", nullable=False)
    op.create_index(op.f("ix_policies_tenant_id"), pt("policies"), ["tenant_id"], unique=False)
    op.create_foreign_key(
        "fk_policies_tenant_id_tenants",
        pt("policies"),
        pt("tenants"),
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.add_column(
        pt("jobs"),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute(
        sa.text(
            f"UPDATE {pt('jobs')} SET tenant_id = {pt('policies')}.tenant_id "
            f"FROM {pt('policies')} WHERE {pt('jobs')}.policy_id = {pt('policies')}.id"
        )
    )
    op.execute(sa.text(f"UPDATE {pt('jobs')} SET tenant_id = '{_DEFAULT_TENANT}'::uuid WHERE tenant_id IS NULL"))
    op.alter_column(pt("jobs"), "tenant_id", nullable=False)
    op.create_index(op.f("ix_jobs_tenant_id"), pt("jobs"), ["tenant_id"], unique=False)
    op.create_foreign_key(
        "fk_jobs_tenant_id_tenants",
        pt("jobs"),
        pt("tenants"),
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    bind = op.get_bind()
    insp = sa.inspect(bind)
    dropped_idempotency_uc = False
    for uc in insp.get_unique_constraints(pt("jobs")) or []:
        cols = set(uc.get("column_names") or ())
        if cols == {"idempotency_key"}:
            op.drop_constraint(uc["name"], pt("jobs"), type_="unique")
            dropped_idempotency_uc = True
            break
    if not dropped_idempotency_uc:
        # Pre-prefix installs used ``jobs_idempotency_key``; fresh installs use ``devault_jobs_*``.
        op.execute(sa.text(f'ALTER TABLE {pt("jobs")} DROP CONSTRAINT IF EXISTS jobs_idempotency_key_key'))
        op.execute(sa.text(f'ALTER TABLE {pt("jobs")} DROP CONSTRAINT IF EXISTS devault_jobs_idempotency_key_key'))
    op.create_unique_constraint(
        "uq_jobs_tenant_id_idempotency_key",
        pt("jobs"),
        ["tenant_id", "idempotency_key"],
    )

    op.add_column(
        pt("schedules"),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute(
        sa.text(
            f"UPDATE {pt('schedules')} SET tenant_id = {pt('policies')}.tenant_id "
            f"FROM {pt('policies')} WHERE {pt('schedules')}.policy_id = {pt('policies')}.id"
        )
    )
    op.alter_column(pt("schedules"), "tenant_id", nullable=False)
    op.create_index(op.f("ix_schedules_tenant_id"), pt("schedules"), ["tenant_id"], unique=False)
    op.create_foreign_key(
        "fk_schedules_tenant_id_tenants",
        pt("schedules"),
        pt("tenants"),
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.add_column(
        pt("artifacts"),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute(
        sa.text(
            f"UPDATE {pt('artifacts')} SET tenant_id = {pt('jobs')}.tenant_id "
            f"FROM {pt('jobs')} WHERE {pt('artifacts')}.job_id = {pt('jobs')}.id"
        )
    )
    op.alter_column(pt("artifacts"), "tenant_id", nullable=False)
    op.create_index(op.f("ix_artifacts_tenant_id"), pt("artifacts"), ["tenant_id"], unique=False)
    op.create_foreign_key(
        "fk_artifacts_tenant_id_tenants",
        pt("artifacts"),
        pt("tenants"),
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_artifacts_tenant_id_tenants", pt("artifacts"), type_="foreignkey")
    op.drop_index(op.f("ix_artifacts_tenant_id"), table_name=pt("artifacts"))
    op.drop_column(pt("artifacts"), "tenant_id")

    op.drop_constraint("fk_schedules_tenant_id_tenants", pt("schedules"), type_="foreignkey")
    op.drop_index(op.f("ix_schedules_tenant_id"), table_name=pt("schedules"))
    op.drop_column(pt("schedules"), "tenant_id")

    op.drop_constraint("uq_jobs_tenant_id_idempotency_key", pt("jobs"), type_="unique")
    op.create_unique_constraint(None, pt("jobs"), ["idempotency_key"])
    op.drop_constraint("fk_jobs_tenant_id_tenants", pt("jobs"), type_="foreignkey")
    op.drop_index(op.f("ix_jobs_tenant_id"), table_name=pt("jobs"))
    op.drop_column(pt("jobs"), "tenant_id")

    op.drop_constraint("fk_policies_tenant_id_tenants", pt("policies"), type_="foreignkey")
    op.drop_index(op.f("ix_policies_tenant_id"), table_name=pt("policies"))
    op.drop_column(pt("policies"), "tenant_id")

    op.drop_table(pt("tenants"))
