from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from devault.db.base import Base
from devault.db.constants import prefixed_fk as fk


class AgentEnrollment(Base):
    """Admin-provisioned binding: ``agent_id`` may only touch jobs/artifacts in ``allowed_tenant_ids`` over gRPC."""

    __tablename__ = "agent_enrollments"

    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    allowed_tenant_ids: Mapped[list] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class EdgeAgent(Base):
    """Last-known Agent identity from gRPC Heartbeat / Register (fleet inventory)."""

    __tablename__ = "edge_agents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    agent_release: Mapped[str | None] = mapped_column(String(64), nullable=True)
    proto_package: Mapped[str | None] = mapped_column(String(128), nullable=True)
    git_commit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_register_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    host_os: Mapped[str | None] = mapped_column(String(255), nullable=True)
    region: Mapped[str | None] = mapped_column(String(128), nullable=True)
    agent_env: Mapped[str | None] = mapped_column(String(128), nullable=True)
    backup_path_allowlist: Mapped[list | None] = mapped_column(JSONB, nullable=True)


class AgentPool(Base):
    """Tenant-scoped pool of edge Agent UUIDs for policy execution binding (failover group)."""

    __tablename__ = "agent_pools"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk("tenants", "id"), ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    members: Mapped[list["AgentPoolMember"]] = relationship(
        "AgentPoolMember",
        back_populates="pool",
        cascade="all, delete-orphan",
    )


class AgentPoolMember(Base):
    """Member of an :class:`AgentPool` with optional dispatch hints (weight / sort_order)."""

    __tablename__ = "agent_pool_members"

    pool_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk("agent_pools", "id"), ondelete="CASCADE"),
        primary_key=True,
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    weight: Mapped[int] = mapped_column(Integer(), nullable=False, default=100)
    sort_order: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)

    pool: Mapped["AgentPool"] = relationship("AgentPool", back_populates="members")


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    require_encrypted_artifacts: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    kms_envelope_key_id: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    s3_bucket: Mapped[str | None] = mapped_column(String(255), nullable=True)
    s3_assume_role_arn: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    s3_assume_role_external_id: Mapped[str | None] = mapped_column(String(1224), nullable=True)
    policy_paths_allowlist_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="off")
    require_mfa_for_admins: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    sso_oidc_issuer: Mapped[str | None] = mapped_column(Text(), nullable=True)
    sso_oidc_audience: Mapped[str | None] = mapped_column(Text(), nullable=True)
    sso_oidc_role_claim: Mapped[str] = mapped_column(String(64), nullable=False, default="devault_role")
    sso_oidc_email_claim: Mapped[str] = mapped_column(String(64), nullable=False, default="email")
    sso_password_login_disabled: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    sso_jit_provisioning: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    sso_saml_entity_id: Mapped[str | None] = mapped_column(Text(), nullable=True)
    sso_saml_acs_url: Mapped[str | None] = mapped_column(Text(), nullable=True)

    policies: Mapped[list["Policy"]] = relationship("Policy", back_populates="tenant")
    jobs: Mapped[list["Job"]] = relationship("Job", back_populates="tenant")


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk("tenants", "id"), ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    plugin: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    bound_agent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    bound_agent_pool_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk("agent_pools", "id"), ondelete="SET NULL"),
        nullable=True,
    )

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="policies")
    schedules: Mapped[list["Schedule"]] = relationship(
        "Schedule",
        back_populates="policy",
        cascade="all, delete-orphan",
    )


class RestoreDrillSchedule(Base):
    """Cron-driven automated restore drills (verify artifact recoverability on Agent disk)."""

    __tablename__ = "restore_drill_schedules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk("tenants", "id"), ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk("artifacts", "id"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cron_expression: Mapped[str] = mapped_column(String(128), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    drill_base_path: Mapped[str] = mapped_column(Text(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Schedule(Base):
    __tablename__ = "schedules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk("tenants", "id"), ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk("policies", "id"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cron_expression: Mapped[str] = mapped_column(String(128), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    policy: Mapped["Policy"] = relationship("Policy", back_populates="schedules")


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("tenant_id", "idempotency_key", name="uq_jobs_tenant_id_idempotency_key"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk("tenants", "id"), ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    plugin: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    policy_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    trigger: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    config_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    restore_artifact_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lease_agent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    lease_agent_hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    completed_agent_hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    bundle_wip_multipart_upload_id: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    bundle_wip_content_length: Mapped[int | None] = mapped_column(BigInteger(), nullable=True)
    bundle_wip_part_size_bytes: Mapped[int | None] = mapped_column(BigInteger(), nullable=True)
    result_meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="jobs")
    artifact: Mapped["Artifact | None"] = relationship(
        "Artifact",
        back_populates="job",
        uselist=False,
    )


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk("tenants", "id"), ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(fk("jobs", "id"), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    storage_backend: Mapped[str] = mapped_column(String(16), nullable=False)
    bundle_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    manifest_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    compression: Mapped[str] = mapped_column(String(32), nullable=False, default="tar.gz")
    encrypted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    retain_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    legal_hold: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)

    job: Mapped["Job"] = relationship("Job", back_populates="artifact")
