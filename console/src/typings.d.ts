declare namespace API {
  /** 与 `GET /api/v1/auth/session`（`AuthSessionOut`）一致。 */
  interface CurrentUser {
    role: 'admin' | 'operator' | 'auditor';
    principal_label: string;
    /** UUID 字符串数组；admin 全租户时为 `null`。 */
    allowed_tenant_ids: string[] | null;
    principal_kind?: 'platform' | 'tenant_user';
    user_id?: string | null;
    email?: string | null;
    /** IAM `name` 或邮箱，用于顶栏展示；缺省时用 `principal_label`。 */
    display_name?: string | null;
    /** IAM access token 中的 `perm` 列表。 */
    permissions?: string[] | null;
    tenants?: Array<{
      tenant_id: string;
      slug: string;
      name: string;
      membership_role: 'tenant_admin' | 'operator' | 'auditor';
      require_mfa_for_admins?: boolean;
      sso_password_login_disabled?: boolean;
    }> | null;
    /** 为 true 时需完成 TOTP 第二步后才能写操作。 */
    needs_mfa?: boolean;
  }

  /** `GET /api/v1/tenants` 单行。 */
  interface TenantRow {
    id: string;
    name: string;
    slug: string;
  }

  /** `GET /version` 控制面版本信息。 */
  interface VersionInfo {
    service: string;
    version: string;
    api: string;
    grpc_proto_package?: string;
    git_sha?: string;
  }

  /** `GET /api/v1/jobs` 列表项（与 `JobOut` 对齐的常用字段）。 */
  interface JobRow {
    id: string;
    tenant_id: string;
    kind: string;
    status: string;
    plugin: string;
    trigger: string;
    created_at: string;
    error_code: string | null;
    error_message: string | null;
  }

  /** `JobOut` 全量（作业中心 / 工作台）。 */
  interface JobOut extends JobRow {
    policy_id: string | null;
    config_snapshot: Record<string, unknown>;
    restore_artifact_id: string | null;
    lease_agent_id: string | null;
    lease_agent_hostname: string | null;
    completed_agent_hostname: string | null;
    lease_expires_at: string | null;
    started_at: string | null;
    finished_at: string | null;
    trace_id: string | null;
    result_meta: Record<string, unknown> | null;
  }

  /** `PolicyOut`（列表 / 表单初始值）。 */
  interface PolicyOut {
    id: string;
    tenant_id: string;
    name: string;
    plugin: string;
    config: Record<string, unknown>;
    enabled: boolean;
    created_at: string;
    updated_at: string | null;
    bound_agent_id: string | null;
  }

  /** `GET /api/v1/agent-tokens` 列表项（`AgentTokenOut`）。 */
  interface AgentTokenOut {
    id: string;
    tenant_id: string;
    label: string;
    description: string | null;
    expires_at: string | null;
    disabled_at: string | null;
    created_at: string;
    updated_at: string;
    last_used_at: string | null;
    instance_count: number;
  }

  /** `POST /api/v1/agent-tokens` 响应（含一次性明文密钥）。 */
  interface AgentTokenCreatedOut {
    id: string;
    tenant_id: string;
    label: string;
    description: string | null;
    expires_at: string | null;
    created_at: string;
    plaintext_secret: string;
    instance_count: number;
  }

  /** `ArtifactOut`。 */
  interface ArtifactOut {
    id: string;
    tenant_id: string;
    job_id: string;
    /** 缺省表示迁移前制品或未回填；读路径按当前激活 profile 解析。 */
    storage_profile_id?: string | null;
    storage_backend: string;
    bundle_key: string;
    manifest_key: string;
    size_bytes: number;
    checksum_sha256: string;
    compression: string;
    encrypted: boolean;
    created_at: string;
    retain_until: string | null;
    legal_hold: boolean;
  }

  interface ScheduleOut {
    id: string;
    tenant_id: string;
    policy_id: string;
    cron_expression: string;
    timezone: string;
    enabled: boolean;
    created_at: string;
  }

  interface RestoreDrillScheduleOut {
    id: string;
    tenant_id: string;
    artifact_id: string;
    cron_expression: string;
    timezone: string;
    enabled: boolean;
    drill_base_path: string;
    created_at: string;
  }

  interface TenantScopedAgentOut {
    id: string;
    allowed_tenant_ids: string[];
    first_seen_at: string | null;
    last_seen_at: string | null;
    agent_release: string | null;
    proto_package: string | null;
    git_commit: string | null;
    last_register_at: string | null;
    meets_min_supported_version: boolean;
    proto_matches_control_plane: boolean;
    hostname: string | null;
    os: string | null;
    region: string | null;
    env: string | null;
    backup_path_allowlist: string[] | null;
  }

  interface AgentPoolOut {
    id: string;
    tenant_id: string;
    name: string;
    created_at: string;
  }

  interface AgentPoolMemberOut {
    agent_id: string;
    weight: number;
    sort_order: number;
    last_seen_at: string | null;
  }

  interface AgentPoolDetailOut extends AgentPoolOut {
    members: AgentPoolMemberOut[];
  }

  interface EdgeAgentOut {
    id: string;
    first_seen_at: string;
    last_seen_at: string;
    agent_release: string | null;
    proto_package: string | null;
    git_commit: string | null;
    last_register_at: string | null;
    meets_min_supported_version: boolean;
    proto_matches_control_plane: boolean;
    allowed_tenant_ids: string[] | null;
    hostname: string | null;
    os: string | null;
    region: string | null;
    env: string | null;
    backup_path_allowlist: string[] | null;
  }

  /** `TenantOut`（管理员列表）。 */
  interface TenantOut extends TenantRow {
    created_at: string;
    require_encrypted_artifacts: boolean;
    kms_envelope_key_id: string | null;
    policy_paths_allowlist_mode: 'off' | 'enforce' | 'warn';
    require_mfa_for_admins?: boolean;
    sso_oidc_issuer?: string | null;
    sso_oidc_audience?: string | null;
    sso_oidc_role_claim?: string;
    sso_oidc_email_claim?: string;
    sso_password_login_disabled?: boolean;
    sso_jit_provisioning?: boolean;
    sso_saml_entity_id?: string | null;
    sso_saml_acs_url?: string | null;
  }
}
