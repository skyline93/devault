from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Self

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DEVAULT_",
        env_file=".env",
        extra="ignore",
    )

    database_url: str = Field(
        default="postgresql+psycopg://devault:devault@localhost:5432/devault",
        description="SQLAlchemy URL for platform metadata DB",
    )
    redis_url: str = Field(default="redis://localhost:6379/0")

    api_token: str | None = Field(default=None, description="If set, require Authorization: Bearer")

    storage_backend: str = Field(default="local", description="local | s3")
    local_storage_root: str = Field(default="./data/storage")

    s3_endpoint: str | None = Field(default=None, description="MinIO/S3 endpoint URL")
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    s3_bucket: str = "devault"
    s3_region: str = "us-east-1"
    s3_use_ssl: bool = False

    # STS AssumeRole for control-plane S3 (optional; see website/docs/storage/sts-assume-role.md)
    s3_assume_role_arn: str | None = Field(
        default=None,
        description="If set, control plane calls STS AssumeRole and uses returned creds for S3",
    )
    s3_assume_role_external_id: str | None = Field(
        default=None,
        description="Optional ExternalId for cross-account AssumeRole",
    )
    s3_assume_role_session_name: str = Field(
        default="devault-control-plane",
        description="RoleSessionName for AssumeRole (max 64 chars; truncated if longer)",
    )
    s3_assume_role_duration_seconds: int = Field(
        default=3600,
        ge=900,
        le=43200,
        description="AssumeRole DurationSeconds (AWS allows 900–43200 for most roles)",
    )
    s3_sts_region: str | None = Field(
        default=None,
        description="STS client region; defaults to s3_region when unset",
    )
    s3_sts_endpoint_url: str | None = Field(
        default=None,
        description="Custom STS endpoint (e.g. LocalStack); omit for AWS regional STS",
    )
    s3_sts_use_ssl: bool = Field(
        default=True,
        description="Use TLS for STS client; set false only for http STS endpoints (e.g. some lab setups)",
    )

    env_name: str = Field(default="dev", description="Key prefix segment dev|prod")

    default_tenant_slug: str = Field(
        default="default",
        description="When HTTP header X-DeVault-Tenant-Id is omitted, resolve tenant by this slug",
    )

    # --- Optional OIDC (Bearer JWT from enterprise IdP) ---
    oidc_issuer: str | None = Field(
        default=None,
        description="If set with oidc_audience, try OIDC JWT validation before static API tokens",
    )
    oidc_audience: str | None = Field(
        default=None,
        description="JWT aud claim required when validating OIDC tokens",
    )
    oidc_role_claim: str = Field(
        default="devault_role",
        description="JWT claim for role: admin | operator | auditor",
    )
    oidc_tenant_ids_claim: str = Field(
        default="devault_tenant_ids",
        description="JWT claim: list of tenant UUID strings (ignored for admin; required scope for operator/auditor)",
    )

    allowed_path_prefixes: str | None = Field(
        default=None,
        description="Comma-separated absolute path prefixes; if set, backup paths must match one",
    )

    grpc_listen: str | None = Field(
        default=None,
        description="Enable Agent gRPC server, e.g. 0.0.0.0:50051 (empty disables)",
    )
    grpc_target: str | None = Field(
        default=None,
        description="Agent only: control plane address host:port for gRPC",
    )

    # --- gRPC server (control plane): TLS + optional mTLS ---
    grpc_server_tls_cert_path: str | None = Field(
        default=None,
        description="PEM server certificate chain for gRPC TLS (with grpc_server_tls_key_path)",
    )
    grpc_server_tls_key_path: str | None = Field(
        default=None,
        description="PEM private key for gRPC server TLS",
    )
    grpc_server_tls_client_ca_path: str | None = Field(
        default=None,
        description="If set, require client certificates signed by this CA (mTLS)",
    )

    # --- gRPC server: rate limit + audit ---
    grpc_rps_per_peer: float = Field(
        default=0.0,
        ge=0.0,
        description="Max sustained RPCs per second per gRPC peer(); 0 disables",
    )
    grpc_rps_burst_per_peer: float = Field(
        default=40.0,
        ge=1.0,
        description="Token bucket burst for grpc_rps_per_peer",
    )
    grpc_audit_log: bool = Field(
        default=True,
        description="Emit JSON lines to logger devault.grpc.audit for each Agent RPC",
    )

    # --- gRPC Register bootstrap (control plane + Agent) ---
    grpc_registration_secret: str | None = Field(
        default=None,
        description="If set, Register RPC accepts this secret and mints a per-Agent Redis bearer token",
    )
    grpc_agent_session_ttl_seconds: int = Field(
        default=604800,
        ge=120,
        description="TTL for Register-minted Agent gRPC Bearer tokens (Redis); refreshed on each RPC",
    )
    grpc_min_supported_agent_version: str = Field(
        default="0.1.0",
        description="Minimum Agent SemVer on Heartbeat/Register; empty agent_release skips semver unless require flag",
    )
    grpc_max_tested_agent_version: str = Field(
        default="",
        description="Maximum Agent SemVer treated as tested; empty means same as control plane release",
    )
    grpc_upgrade_url: str | None = Field(
        default=None,
        description="Optional URL for operators; returned to agents on Heartbeat/Register",
    )
    grpc_require_agent_version: bool = Field(
        default=False,
        description="If true, reject Heartbeat/Register when agent_release is empty",
    )
    grpc_enforce_version_on_lease: bool = Field(
        default=True,
        description=(
            "If true, LeaseJobs re-checks version/proto against edge_agents (last Heartbeat); "
            "set false only for break-glass"
        ),
    )
    server_git_sha: str | None = Field(
        default=None,
        description="Optional vcs sha; exposed on GET /version when set",
    )

    # --- gRPC client (Agent): TLS toward gateway or control plane ---
    grpc_tls_ca_path: str | None = Field(
        default=None,
        description="Agent: PEM trust bundle to verify server (enables TLS on channel)",
    )
    grpc_tls_client_cert_path: str | None = Field(
        default=None,
        description="Agent: optional client certificate PEM for mTLS",
    )
    grpc_tls_client_key_path: str | None = Field(
        default=None,
        description="Agent: optional client private key PEM for mTLS",
    )
    grpc_tls_server_name: str | None = Field(
        default=None,
        description="Agent: TLS server name override for certificate verification (SNI)",
    )

    job_lease_ttl_seconds: int = Field(default=1800, ge=60)
    presign_ttl_seconds: int = Field(default=3600, ge=60)
    fleet_agent_stale_seconds: int = Field(
        default=900,
        ge=60,
        le=86400 * 7,
        description="edge_agents last_seen older than this are counted in devault_edge_agents_stale_count (metrics)",
    )

    job_stuck_threshold_seconds: int = Field(
        default=86400,
        ge=300,
        le=864000,
        description=(
            "Jobs in running/uploading/verifying (or pending) longer than this are counted in "
            "devault_jobs_overdue_nonterminal for alerting"
        ),
    )

    # S3 bundle upload (Agent path): multipart when bundle >= threshold (bytes)
    s3_multipart_threshold_bytes: int = Field(
        default=32 * 1024 * 1024,
        ge=1,
        description="Use multipart presigned upload for bundle when size >= this",
    )
    s3_multipart_part_size_bytes: int = Field(
        default=16 * 1024 * 1024,
        ge=5 * 1024 * 1024,
        description="Target part size (S3 requires >= 5MiB except last part)",
    )
    agent_multipart_state_dir: str | None = Field(
        default=None,
        description="Agent only: base directory for multipart resume checkpoints and WIP bundle",
    )
    agent_git_commit: str | None = Field(
        default=None,
        description="Agent only: optional short git SHA sent on Heartbeat/Register",
    )

    # Artifact encryption (AES-256-GCM chunked format); Agent must match control plane policy.
    artifact_encryption_key: str | None = Field(
        default=None,
        description="Base64-encoded 32-byte AES-256 key for bundle encryption at-rest",
    )
    require_encrypted_artifacts: bool = Field(
        default=False,
        description="When true, backup manifests must declare encryption (tenant may tighten further)",
    )
    kms_envelope_key_id: str | None = Field(
        default=None,
        description="Default KMS CMK id or ARN for envelope encryption (tenant may override)",
    )
    kms_region: str | None = Field(
        default=None,
        description="KMS API region; defaults to s3_region when unset",
    )

    retention_cleanup_enabled: bool = Field(
        default=True,
        description="When true, devault-scheduler periodically deletes expired artifacts",
    )
    retention_cleanup_interval_seconds: int = Field(
        default=900,
        ge=60,
        le=86400,
        description="Interval between retention purge runs in the scheduler process",
    )

    @model_validator(mode="after")
    def _s3_key_pair_consistent(self) -> Self:
        ak, sk = self.s3_access_key, self.s3_secret_key
        if (ak is None) ^ (sk is None):
            raise ValueError(
                "DEVAULT_S3_ACCESS_KEY and DEVAULT_S3_SECRET_KEY must be set together or both omitted"
            )
        return self

    @model_validator(mode="after")
    def _grpc_tls_paths_consistent(self) -> Self:
        sc, sk = self.grpc_server_tls_cert_path, self.grpc_server_tls_key_path
        if (sc is None) ^ (sk is None):
            raise ValueError(
                "DEVAULT_GRPC_SERVER_TLS_CERT_PATH and DEVAULT_GRPC_SERVER_TLS_KEY_PATH "
                "must be set together"
            )
        if self.grpc_server_tls_client_ca_path and (sc is None or sk is None):
            raise ValueError(
                "DEVAULT_GRPC_SERVER_TLS_CLIENT_CA_PATH requires server TLS cert and key"
            )
        cc, ck = self.grpc_tls_client_cert_path, self.grpc_tls_client_key_path
        if (cc is None) ^ (ck is None):
            raise ValueError(
                "DEVAULT_GRPC_TLS_CLIENT_CERT_PATH and DEVAULT_GRPC_TLS_CLIENT_KEY_PATH "
                "must be set together"
            )
        return self

    @property
    def agent_multipart_state_root(self) -> Path:
        if self.agent_multipart_state_dir:
            return Path(self.agent_multipart_state_dir).expanduser()
        return Path.home() / ".cache" / "devault-agent"

    @property
    def allowed_prefix_list(self) -> list[str] | None:
        if not self.allowed_path_prefixes:
            return None
        parts = [p.strip() for p in self.allowed_path_prefixes.split(",") if p.strip()]
        return parts or None

    @field_validator("storage_backend")
    @classmethod
    def storage_ok(cls, v: str) -> str:
        v = v.lower()
        if v not in ("local", "s3"):
            raise ValueError("storage_backend must be local or s3")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
