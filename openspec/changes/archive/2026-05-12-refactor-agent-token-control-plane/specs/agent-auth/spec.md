## ADDED Requirements

### Requirement: Tenant Agent token issuance

The control plane SHALL allow authenticated tenant administrators to create Agent tokens scoped to exactly one tenant. Each token SHALL be stored as a one-way hash of the secret; the plaintext secret SHALL be returned only at creation time. Each token SHALL support a human-readable label and description, an optional expiration timestamp, and a disabled state used for revocation.

#### Scenario: Create token with expiry

- **WHEN** a tenant administrator creates an Agent token with a label and a future `expires_at`
- **THEN** the API returns the plaintext secret once and persists the hash, tenant id, label, description, and expiry

#### Scenario: Disable token

- **WHEN** a tenant administrator disables an Agent token
- **THEN** subsequent Agent gRPC calls authenticated with that secret SHALL be rejected

### Requirement: Agent registration with token and host snapshot

An Agent SHALL register with the control plane using its configured long-lived token. The Register request SHALL include version metadata (`agent_release`, `proto_package`, `git_commit`) and host snapshot fields (`hostname`, `os`, `region`, `env`, `backup_path_allowlist`, `snapshot_schema_version`). The control plane SHALL derive the tenant solely from the token, SHALL NOT require pre-provisioned enrollment, and SHALL create or update an `edge_agents` row for the instance.

#### Scenario: First registration allocates agent id

- **WHEN** an Agent registers with a valid token and does not present a previously assigned `agent_id`
- **THEN** the control plane allocates a new `agent_id`, associates the instance with the token, persists the host snapshot, and returns the `agent_id`

#### Scenario: Re-registration updates snapshot for same instance

- **WHEN** an Agent registers again with the same valid token and the same persisted `agent_id`
- **THEN** the control plane updates the host snapshot and registration timestamps without creating a duplicate instance row

### Requirement: Long-lived bearer on Agent gRPC

All Agent gRPC methods SHALL authenticate via `Authorization: Bearer` using the long-lived Agent token. The control plane SHALL NOT mint Redis-scoped Agent session tokens for Register or Heartbeat. Successful authentication SHALL yield a principal scoped to the token’s single tenant.

#### Scenario: Heartbeat with valid token

- **WHEN** an Agent sends Heartbeat with a valid, non-disabled, unexpired token and a known `agent_id` for that token
- **THEN** the RPC succeeds and the control plane updates only liveness (and version columns per the version-sync rule)

#### Scenario: Invalid token rejected

- **WHEN** an Agent presents a wrong, disabled, or expired token on any Agent gRPC method
- **THEN** the RPC fails with an unauthenticated error

### Requirement: Heartbeat version gate without snapshot mutation

On every Heartbeat, the control plane SHALL validate `agent_release` and `proto_package` against the same version gate used on Register. Heartbeat SHALL NOT modify host snapshot columns (`hostname`, `os`, `region`, `env`, `backup_path_allowlist`). When validation passes and version fields differ from stored values, the control plane MAY update only `agent_release`, `proto_package`, and `git_commit` on the `edge_agents` row.

#### Scenario: Proto mismatch fails Heartbeat

- **WHEN** an Agent sends Heartbeat with a `proto_package` that does not match the control plane expectation
- **THEN** the RPC fails before updating `last_seen_at`

#### Scenario: Upgrade updates version columns only

- **WHEN** an Agent Heartbeat reports a newer valid `agent_release` after an in-place upgrade
- **THEN** the control plane updates version columns and `last_seen_at` but leaves host snapshot columns unchanged

### Requirement: One token multiple instances

A single Agent token SHALL be allowed to register multiple distinct `agent_id` values. Fleet and audit views SHALL be able to list instances grouped by token metadata.

#### Scenario: Second host uses same token

- **WHEN** a second Agent process registers with the same valid token and no conflicting persisted `agent_id`
- **THEN** the control plane creates a second `edge_agents` row linked to the same token

## REMOVED Requirements

### Requirement: Agent enrollment before Register

**Reason**: Tenant scope and legitimacy are carried by the Agent token; pre-provisioned `agent_enrollments` and `allowed_tenant_ids` are redundant.

**Migration**: Issue Agent tokens via console/API; register instances; remove enrollment REST/UI and seeds.

### Requirement: Redis-backed Agent gRPC session minting

**Reason**: Agents use long-lived bearer tokens; session TTL and per-agent generation revocation are unnecessary for Agent authentication.

**Migration**: Remove Register reply session minting, `agent_grpc_session` helpers, and `revoke-grpc-sessions` endpoints; disable tokens instead.

### Requirement: Agent pool execution binding

**Reason**: Execution routing is exclusively single-Agent policy binding.

**Migration**: Delete pool tables and APIs; set `bound_agent_id` on each policy; remove `bound_agent_pool_id`.

## MODIFIED Requirements

### Requirement: Policy execution binding

Each policy SHALL set `bound_agent_id` to exactly one registered Agent instance in the policy’s tenant. The field SHALL be required on policy create and update. Multiple policies MAY reference the same `bound_agent_id`. An Agent instance SHALL only lease jobs whose policy’s `bound_agent_id` equals that instance’s `agent_id`. Policies SHALL NOT use Agent pools or unbound execution routing.

#### Scenario: Bound policy job visible only to bound agent

- **WHEN** a pending job references a policy with `bound_agent_id` set to agent A
- **THEN** LeaseJobs for agent A may return the job and LeaseJobs for agent B in the same tenant SHALL NOT return the job

#### Scenario: Agent does not lease unbound policy jobs

- **WHEN** a policy has no `bound_agent_id` or the bound agent is not registered for the tenant
- **THEN** jobs for that policy SHALL NOT be leased until binding is valid

#### Scenario: Multiple policies share one agent

- **WHEN** two policies in the same tenant both set `bound_agent_id` to agent A
- **THEN** agent A may lease jobs from either policy subject to tenant scope and existing job-kind rules
