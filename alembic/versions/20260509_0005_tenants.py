"""Tenants table; tenant_id on policies, jobs, schedules, artifacts; S3 key isolation."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

_DEFAULT_TENANT = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    op.create_table(
        "tenants",
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
            "INSERT INTO tenants (id, name, slug) VALUES "
            f"('{_DEFAULT_TENANT}'::uuid, 'Default', 'default')"
        )
    )

    op.add_column(
        "policies",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute(sa.text(f"UPDATE policies SET tenant_id = '{_DEFAULT_TENANT}'::uuid"))
    op.alter_column("policies", "tenant_id", nullable=False)
    op.create_index(op.f("ix_policies_tenant_id"), "policies", ["tenant_id"], unique=False)
    op.create_foreign_key(
        "fk_policies_tenant_id_tenants",
        "policies",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.add_column(
        "jobs",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE jobs SET tenant_id = policies.tenant_id "
            "FROM policies WHERE jobs.policy_id = policies.id"
        )
    )
    op.execute(sa.text(f"UPDATE jobs SET tenant_id = '{_DEFAULT_TENANT}'::uuid WHERE tenant_id IS NULL"))
    op.alter_column("jobs", "tenant_id", nullable=False)
    op.create_index(op.f("ix_jobs_tenant_id"), "jobs", ["tenant_id"], unique=False)
    op.create_foreign_key(
        "fk_jobs_tenant_id_tenants",
        "jobs",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    bind = op.get_bind()
    insp = sa.inspect(bind)
    for uc in insp.get_unique_constraints("jobs") or []:
        cols = set(uc.get("column_names") or ())
        if cols == {"idempotency_key"}:
            op.drop_constraint(uc["name"], "jobs", type_="unique")
            break
    else:
        op.drop_constraint("jobs_idempotency_key_key", "jobs", type_="unique")
    op.create_unique_constraint(
        "uq_jobs_tenant_id_idempotency_key",
        "jobs",
        ["tenant_id", "idempotency_key"],
    )

    op.add_column(
        "schedules",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE schedules SET tenant_id = policies.tenant_id "
            "FROM policies WHERE schedules.policy_id = policies.id"
        )
    )
    op.alter_column("schedules", "tenant_id", nullable=False)
    op.create_index(op.f("ix_schedules_tenant_id"), "schedules", ["tenant_id"], unique=False)
    op.create_foreign_key(
        "fk_schedules_tenant_id_tenants",
        "schedules",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.add_column(
        "artifacts",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE artifacts SET tenant_id = jobs.tenant_id FROM jobs WHERE artifacts.job_id = jobs.id"
        )
    )
    op.alter_column("artifacts", "tenant_id", nullable=False)
    op.create_index(op.f("ix_artifacts_tenant_id"), "artifacts", ["tenant_id"], unique=False)
    op.create_foreign_key(
        "fk_artifacts_tenant_id_tenants",
        "artifacts",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_artifacts_tenant_id_tenants", "artifacts", type_="foreignkey")
    op.drop_index(op.f("ix_artifacts_tenant_id"), table_name="artifacts")
    op.drop_column("artifacts", "tenant_id")

    op.drop_constraint("fk_schedules_tenant_id_tenants", "schedules", type_="foreignkey")
    op.drop_index(op.f("ix_schedules_tenant_id"), table_name="schedules")
    op.drop_column("schedules", "tenant_id")

    op.drop_constraint("uq_jobs_tenant_id_idempotency_key", "jobs", type_="unique")
    op.create_unique_constraint(None, "jobs", ["idempotency_key"])
    op.drop_constraint("fk_jobs_tenant_id_tenants", "jobs", type_="foreignkey")
    op.drop_index(op.f("ix_jobs_tenant_id"), table_name="jobs")
    op.drop_column("jobs", "tenant_id")

    op.drop_constraint("fk_policies_tenant_id_tenants", "policies", type_="foreignkey")
    op.drop_index(op.f("ix_policies_tenant_id"), table_name="policies")
    op.drop_column("policies", "tenant_id")

    op.drop_table("tenants")
