# Change: Refactor Agent–Control Plane Authentication and Policy Binding

## Why

The current Agent onboarding model requires administrators to pre-provision `agent_id` rows in `agent_enrollments`, align a fixed `DEVAULT_AGENT_ID` (or random UUID) with that enrollment, and exchange a global `DEVAULT_GRPC_REGISTRATION_SECRET` for a short-lived Redis gRPC session. This is operationally heavy, easy to misconfigure in Compose and IaC, and diverges from the product intent: **tenant operators issue Agent credentials in the console; edge hosts register with that credential; all gRPC traffic uses the same long-lived bearer bound to a single tenant**.

The model also couples execution routing to Agent pools and optional unbound policies, which adds UI and SQL complexity without matching the desired **one policy → one Agent instance** execution contract.

## What Changes

- **BREAKING**: Remove `agent_enrollments`, enrollment REST/UI, global registration-secret bootstrap, Redis-backed per-Agent gRPC sessions, and `revoke-grpc-sessions` by session generation.
- **BREAKING**: Remove Agent pools (`agent_pools`, `agent_pool_members`, `policies.bound_agent_pool_id`, pool REST/UI, and pool-aware `LeaseJobs` filtering).
- **BREAKING**: Require every policy to set `bound_agent_id`; an Agent instance may only lease jobs whose policy binds that `agent_id` (and may be bound by multiple policies).
- Add tenant-scoped **Agent tokens** (long-lived bearer secrets stored hashed in the control plane DB; optional expiry; user-visible label/description; disable for revocation).
- **Register** authenticates with the Agent token, accepts version metadata and host snapshot fields, allocates or confirms `agent_id`, and persists `edge_agents` without pre-provisioning.
- **Heartbeat** validates version/proto on every request but persists only `last_seen_at` (and may update version columns when the running binary changes, without rewriting host snapshot columns).
- All Agent gRPC calls use `Authorization: Bearer <agent token>`; tenant scope is derived from the token row, not from `allowed_tenant_ids` enrollment lists.
- Console: generate/list/disable Agent tokens; fleet views keyed by registered instances and token metadata; policy editor binds a single registered Agent (no pools, no enrollment forms).
- Agent process configuration: token + control plane target only (no default `DEVAULT_AGENT_ID`, no enrollment prerequisite).

## Impact

- Affected specs (deltas in this change): `agent-auth`, `agent-policy-execution`
- Affected code (non-exhaustive):
  - `proto/agent.proto`, `src/devault/grpc/servicer.py`, `src/devault/agent/main.py`
  - `src/devault/security/agent_grpc_session.py` (remove or replace)
  - `src/devault/db/models.py`, Alembic migrations
  - `src/devault/api/routes/agents.py`, `agent_pools.py` (remove), new Agent token routes
  - `src/devault/services/agent_enrollment.py`, `policy_execution_binding.py`, `tenant_backup_allowlist.py`, `edge_agents.py`
  - `console/` execution and policy pages; OpenAPI types
  - `deploy/docker-compose.yml`, `deploy/iac/examples/`, `scripts/e2e_grpc_register_heartbeat.py`
  - `website/docs/` agent fleet, gRPC（**`reference/grpc-services.md`** 含 Mermaid「时序概览」）, agent pools, credential lifecycle, quickstart
  - `CHANGELOG.md` **`[Unreleased]`**（与本变更一致的 Added / Removed / Changed / Fixed 摘要）
- **Demo stack (follow-up)**: `demo-stack-init` should optionally create a tenant Agent token **via public HTTP** (`POST /api/v1/agent-tokens` with the same IAM Bearer + `X-DeVault-Tenant-Id` used for tenant mirror), without altering the IAM→DeVault tenant mirror success path; persist the one-time `plaintext_secret` for the `agent` service (e.g. shared volume + file) so `make demo-stack-up` works without hand-pasting a bearer.
- **Out of scope**: IAM human login and HTTP API JWT validation; Agent data-plane object storage grants; Redis policy job locks for backup mutual exclusion (retained unless separately removed).

## Compatibility

Greenfield replacement of the enrollment + Redis session + Agent pool model. Existing deployments must re-issue Agent tokens, re-register instances, re-bind policies to concrete `agent_id` values, and drop pool bindings before upgrade.
