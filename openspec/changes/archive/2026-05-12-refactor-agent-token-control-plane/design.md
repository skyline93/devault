## Context

DeVault edge Agents connect to the control plane over gRPC (Pull: Register/Heartbeat, LeaseJobs, storage grants, completion). Today, identity is split across:

- Admin-provisioned `agent_enrollments` (`allowed_tenant_ids` per `agent_id`)
- A shared `DEVAULT_GRPC_REGISTRATION_SECRET` on Register
- Redis opaque session tokens minted after Register (`devault:grpc:sess:*`, generation counters per `agent_id`)
- Optional Agent pools and optional unbound policies for `LeaseJobs` routing

Operators want a **tenant-console-issued Agent token** that edge hosts configure once. The control plane infers tenant scope from the token, registers instances without placeholders, and uses the **same bearer** for all Agent RPCs. Revocation is **disable the token**. Agent gRPC remains **independent of IAM** (console HTTP continues to use IAM).

## Goals / Non-Goals

### Goals

- Tenant operators create Agent tokens (label/description, optional expiry, disable/re-enable) via authenticated HTTP APIs and console UI.
- Agents register with token + version metadata + host snapshot; control plane assigns or confirms `agent_id` and writes `edge_agents`.
- One token may register **multiple** Agent instances (distinct `agent_id` per host/process), all scoped to the **same tenant**.
- Long-lived bearer on every Agent gRPC call; validation against DB hash + disabled/expired state.
- Remove enrollment, global registration secret as the primary bootstrap, Redis gRPC sessions, and Agent pools.
- Policies **must** bind exactly one `bound_agent_id`; multiple policies may reference the same Agent; `LeaseJobs` is narrowed both ways (policy → Agent and Agent → policy).
- Heartbeat: **validate** `agent_release` / `proto_package` every tick; **persist** only liveness timestamp (and version columns when the running binary changes); **do not** update host snapshot columns on Heartbeat.
- Preserve version negotiation replies (`server_release`, min/max tested, capabilities) and hard failures on proto mismatch / below-minimum version.

### Non-Goals

- IAM Service Account or JWT for Agent gRPC.
- Multi-tenant Agents (one token → one tenant only).
- Short-lived session exchange after Register (no “configure credential → mint Redis bearer” path).
- Replacing Redis **policy job locks** used for backup mutual exclusion on the same `policy_id` (orthogonal to Agent authentication).
- Automatic migration of legacy enrollment rows or pool memberships (greenfield cutover).

## Decisions

### Decision: Agent token as the sole Agent gRPC credential

- **What**: Store `agent_tokens` with `tenant_id`, `token_hash`, `label`/`description`, `expires_at` (nullable), `disabled_at`, timestamps. Plaintext shown once on create.
- **Why**: Matches console “生成 Agent 令牌”, supports disable-without-touching-host, and binds tenant without `allowed_tenant_ids` arrays.
- **Alternatives**: Reuse IAM API keys (rejected: Agent plane stays in DeVault per `docs/iam-service-design.md`); global `registration_secret` only (rejected: no per-tenant revocation granularity).

### Decision: Long-lived bearer on all Agent RPCs

- **What**: `Authorization: Bearer <agent token>` on Register, Heartbeat, LeaseJobs, and downstream RPCs. No Redis session minting or refresh.
- **Why**: Simplifies agent host config and revocation (disable token).
- **Alternatives**: Register exchanges for Redis TTL bearer (rejected by product intent).

### Decision: Register carries host snapshot; Heartbeat does not mutate snapshot

- **What**: Register (and re-register with persisted `agent_id`) writes `hostname`, `os`, `region`, `env`, `backup_path_allowlist` to `edge_agents`. Heartbeat updates `last_seen_at` only for snapshot columns; still runs `evaluate_agent_version_gate` on request fields.
- **Why**: Path allowlist union and fleet inventory should reflect deliberate registration; heartbeats remain cheap.
- **Version columns**: When Heartbeat validation passes and `agent_release` / `proto_package` / `git_commit` differ from stored values, update **only** those version columns (not host snapshot). This keeps `LeaseJobs` defense-in-depth consistent after in-place upgrades without requiring a full re-register.

### Decision: `agent_id` is runtime identity, not provisioned

- **What**: On first Register with a token, server generates `agent_id` (UUID) unless the client resubmits a previously issued id for the same instance. Persist `edge_agents.id` and `edge_agents.agent_token_id`.
- **Why**: Supports “no placeholder” while keeping lease attribution and policy binding by instance.
- **Alternatives**: Client-only random id without server confirmation (rejected: harder to audit token/instance binding).

### Decision: Policy execution binding is mandatory single Agent

- **What**: `policies.bound_agent_id` required on create/update. Remove `bound_agent_pool_id` and pool tables/APIs/UI. `LeaseJobs` SQL requires `Policy.bound_agent_id == leasing_agent_id` when `job.policy_id` is set.
- **Why**: Explicit routing; multiple policies may share one Agent; Agent does not pick up jobs from policies bound to siblings under the same token.
- **Validation**: `bound_agent_id` must reference an `edge_agents` row whose `agent_token_id` belongs to the policy’s tenant and whose token is not disabled/expired at write time (exact strictness documented in API errors).

### Decision: Remove enrollment and pool subsystems

- **What**: Drop `agent_enrollments`, enrollment routes, fleet enrollment UI, `agent_pools` / `agent_pool_members`, and related tests/docs.
- **Why**: Token + registered instance replaces both concepts.

### Decision: Tenant path allowlist uses registered snapshots

- **What**: `union_backup_path_allowlist_for_tenant` enumerates `edge_agents.backup_path_allowlist` for instances whose token’s `tenant_id` matches (not enrollment JSON).
- **Why**: Preserves tenant `policy_paths_allowlist_mode` behavior after enrollment removal.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Long-lived token leakage grants tenant-scoped Agent RPC until disabled | HTTPS/TLS to gateway; disable token; short optional expiry; never log bearer; document host secret storage |
| One token → many instances complicates fleet mental model | Token detail UI shows instance list; optional `label` on token |
| Heartbeat without snapshot refresh stale host metadata | Re-register after material host/path changes |
| Breaking change for existing deployments | Explicit migration runbook in tasks; remove Compose default `DEVAULT_AGENT_ID` and enrollment seeds |
| DB lookup per gRPC vs Redis session | Acceptable for MVP; optional in-process cache later without changing contract |

## Migration Plan

1. Ship schema: `agent_tokens`, `edge_agents.agent_token_id`; drop enrollment/pool tables and policy pool column.
2. Implement token CRUD + gRPC auth + Register/Heartbeat semantics.
3. Tighten policy binding validation and `LeaseJobs` filter.
4. Update Agent binary, console, compose, e2e, docs.
5. Delete dead code paths (`agent_grpc_session`, enrollment services, pool routes).
6. Rollback: restore previous release; DB restore required (no dual-write period in this change).

## Open Questions

- Whether to expose per-instance disable (blacklist `agent_id`) in addition to token disable — **deferred**; token disable is sufficient for MVP.
- Jobs without `policy_id` (if any remain) — **default**: not leasable unless a follow-up assigns explicit rules per `kind`.

## Documentation: sequence diagrams

- **What**: Maintain **Mermaid `sequenceDiagram` blocks** in `website/docs/reference/grpc-services.md` under **「时序概览（重构后）」**, covering HTTP token issuance and the main gRPC paths (Register, Heartbeat, LeaseJobs) on a single long-lived Bearer.
- **Why**: Gives operators and reviewers a single visual for the post-refactor Agent ↔ control plane contract without rereading proto and servicer code.

## Demo stack: automatic Agent token (HTTP only)

- **What**: After the existing **`POST /api/v1/tenants`** mirror succeeds (same script, same success/409 semantics), optionally call **`GET`** then **`POST /api/v1/agent-tokens`** using the **same IAM JWT** and **`X-DeVault-Tenant-Id: <mirrored tenant uuid>`**. No direct DB writes from the bootstrap script for token creation (keeps one code path with production REST).
- **Idempotency**: `GET /api/v1/agent-tokens` first; if a token with a fixed demo label (e.g. configurable `DEMO_STACK_AGENT_TOKEN_LABEL`) already exists, **do not** create another row (plaintext is not retrievable on list — see persistence below).
- **Persistence**: On first create only, write `plaintext_secret` from the JSON response to a path on a **Compose shared volume** between `demo-stack-init` and `agent` (e.g. single-line file). The `agent` service uses **`deploy/scripts/devault-agent-docker-entry.sh`** to load that file into `DEVAULT_AGENT_TOKEN` when the env var is unset. Document that non-demo stacks should create tokens via console or `curl` and set env explicitly.
- **Why**: One-command `make demo-stack-up` without manual token copy; HTTP exercises the same RBAC and validation as operators; tenant mirror remains the primary bootstrap step (unchanged ordering and IAM/tenant failure semantics before the token HTTP calls).
