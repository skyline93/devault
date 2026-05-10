"""Align DeVault default tenant id with IAM seed (uuid5 namespace, slug tenant.default).

IAM seeds default tenant id = uuid5(018f0000-0000-7000-8000-000000000001, "tenant.default").
Historical DeVault used 00000000-0000-0000-0000-000000000001. JWT ``tids`` must match ``tenants.id``.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0019"
down_revision = "0012_drop_legacy"
branch_labels = None
depends_on = None

_LEGACY_DEFAULT = "00000000-0000-0000-0000-000000000001"
_IAM_DEFAULT = "62b19263-e820-517e-93fc-c2aeae36ce58"


def upgrade() -> None:
    bind = op.get_bind()
    row = bind.execute(
        sa.text("SELECT id::text FROM tenants WHERE slug = :slug LIMIT 1"),
        {"slug": "default"},
    ).fetchone()
    if row is None:
        return
    current_id = row[0]
    if current_id == _IAM_DEFAULT:
        return
    if current_id != _LEGACY_DEFAULT:
        return

    # Fixed UUID literals (no user input); bind execute via connection for SQLAlchemy 2 style.
    leg, iam = _LEGACY_DEFAULT, _IAM_DEFAULT

    bind.execute(
        sa.text(
            f"UPDATE tenants SET slug = 'default__legacy_pre_iam' "
            f"WHERE id = CAST('{leg}' AS uuid) AND slug = 'default'"
        )
    )

    bind.execute(
        sa.text(
            f"""
            INSERT INTO tenants (
                id, name, slug, created_at,
                require_encrypted_artifacts, kms_envelope_key_id, s3_bucket, s3_assume_role_arn,
                s3_assume_role_external_id, policy_paths_allowlist_mode, require_mfa_for_admins,
                sso_oidc_issuer, sso_oidc_audience, sso_oidc_role_claim, sso_oidc_email_claim,
                sso_password_login_disabled, sso_jit_provisioning, sso_saml_entity_id, sso_saml_acs_url
            )
            SELECT
                CAST('{iam}' AS uuid),
                name,
                'default',
                created_at,
                require_encrypted_artifacts,
                kms_envelope_key_id,
                s3_bucket,
                s3_assume_role_arn,
                s3_assume_role_external_id,
                policy_paths_allowlist_mode,
                require_mfa_for_admins,
                sso_oidc_issuer,
                sso_oidc_audience,
                sso_oidc_role_claim,
                sso_oidc_email_claim,
                sso_password_login_disabled,
                sso_jit_provisioning,
                sso_saml_entity_id,
                sso_saml_acs_url
            FROM tenants
            WHERE id = CAST('{leg}' AS uuid)
            """
        )
    )

    for tbl in (
        "policies",
        "jobs",
        "schedules",
        "artifacts",
        "agent_pools",
        "restore_drill_schedules",
    ):
        bind.execute(
            sa.text(
                f"UPDATE {tbl} SET tenant_id = CAST('{iam}' AS uuid) "
                f"WHERE tenant_id = CAST('{leg}' AS uuid)"
            )
        )

    bind.execute(
        sa.text(
            f"""
            UPDATE agent_enrollments
            SET allowed_tenant_ids = replace(allowed_tenant_ids::text, '{leg}', '{iam}')::jsonb
            WHERE allowed_tenant_ids::text LIKE '%{leg}%'
            """
        )
    )

    bind.execute(sa.text(f"DELETE FROM tenants WHERE id = CAST('{leg}' AS uuid)"))


def downgrade() -> None:
    raise NotImplementedError("tenant UUID alignment downgrade not supported")
