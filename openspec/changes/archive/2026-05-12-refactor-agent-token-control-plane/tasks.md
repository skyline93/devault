## 1. Schema and models

- [x] 1.1 Add `agent_tokens` table (tenant FK, hash, label, description, expires_at, disabled_at, timestamps)
- [x] 1.2 Add `edge_agents.agent_token_id` FK to `agent_tokens`
- [x] 1.3 Drop `agent_enrollments`, `agent_pools`, `agent_pool_members`; remove `policies.bound_agent_pool_id` and related CHECK constraints
- [x] 1.4 Alembic migration with greenfield cutover notes (no enrollment/pool data retention)
- [x] 1.5 Update SQLAlchemy models in `src/devault/db/models.py`

## 2. Agent token HTTP API and console

- [x] 2.1 REST: create (return plaintext once), list, get, disable/enable, optional patch label/description under tenant scope + admin/operator rules
- [x] 2.2 OpenAPI schemas and `console` UI: “生成 Agent 令牌”, token list with remark, disable action, instance count
- [x] 2.3 Remove enrollment routes and fleet enrollment UI; remove agent pool routes and pages

## 3. gRPC contract and servicer

- [x] 3.1 Update `proto/agent.proto`: Register uses agent token (metadata or field), host snapshot fields; deprecate `registration_secret` and Register-issued session fields
- [x] 3.2 Regenerate protobuf stubs (`scripts/gen_proto.sh`)
- [x] 3.3 Implement token authentication helper (hash lookup, tenant scope, disabled/expired checks)
- [x] 3.4 Rewrite `Register`: no enrollment, no Redis mint; allocate/confirm `agent_id`; upsert `edge_agents` snapshot
- [x] 3.5 Rewrite `Heartbeat`: version gate on request; update `last_seen_at`; optional version-column sync; no snapshot mutation
- [x] 3.6 Update `_authenticate_grpc` to use Agent tokens only (remove Redis session + enrollment tenant load)
- [x] 3.7 Remove `revoke-grpc-sessions` API and `agent_grpc_session.py` usage
- [x] 3.8 Tighten `_pending_candidate_ids` / `LeaseJobs` for mandatory `bound_agent_id` match; delete pool EXISTS branch

## 4. Policy binding and tenant allowlist

- [x] 4.1 Require `bound_agent_id` in policy create/patch schemas and `services/control.py`
- [x] 4.2 Replace enrollment checks in `policy_execution_binding.py` with token-tenant + `edge_agents` validation
- [x] 4.3 Rewrite `tenant_backup_allowlist.py` to union snapshots by tenant via `agent_tokens` / `edge_agents`
- [x] 4.4 Update `tenant-agents` and fleet presenters to list registered instances per tenant/token

## 5. Agent process and deployment

- [x] 5.1 `devault-agent`: configure token only; persist returned `agent_id`; remove `DEVAULT_AGENT_ID` and registration-secret bootstrap
- [x] 5.2 `deploy/docker-compose.yml`: remove default `DEVAULT_AGENT_ID` / enrollment comments; document token env var
- [x] 5.3 Update `scripts/e2e_grpc_register_heartbeat.py` and IaC examples (`curl-enroll.sh` → token flow)
- [x] 5.4 `Makefile` / demo bootstrap: create token via API instead of enrollment

## 6. Tests and documentation

- [x] 6.1 Replace `tests/test_agent_enrollment.py` with agent token + Register/Heartbeat/LeaseJobs coverage
- [x] 6.2 Update policy binding and tenant allowlist tests; remove pool tests
- [x] 6.3 Update `website/docs` (grpc-services, agent-fleet, agent-pools removal, credential lifecycle, quickstart, ER diagram)
- [x] 6.4 Run `openspec validate refactor-agent-token-control-plane --strict` and project test suite

## 7. Demo stack: HTTP-issued Agent token for one-command up

**Constraints**: Use **only** DeVault HTTP APIs for token lifecycle in bootstrap (no `SessionLocal` / ORM token mint in `bootstrap_demo_stack.py`). Keep IAM login → IAM tenant → **`POST /api/v1/tenants`** mirror as the **unchanged primary path** (same exit codes on failure). Token step runs **after** successful tenant mirror; failures should be isolated (log + optional non-zero only when agent profile requires a token).

- [x] 7.1 Extend `deploy/scripts/bootstrap_demo_stack.py`: after DeVault tenant upsert succeeds, with IAM Bearer + `X-DeVault-Tenant-Id: <tenant uuid>`, call **`GET /api/v1/agent-tokens`**; if no token matches configurable demo **`label`**, call **`POST /api/v1/agent-tokens`** with `{ "label", "description" }`; parse **`plaintext_secret`** from **`AgentTokenCreatedOut`**.
- [x] 7.2 Persist first-run plaintext to a **shared volume path** (e.g. `DEMO_STACK_AGENT_TOKEN_FILE`, default under a named volume mounted by both `demo-stack-init` and `agent`); on subsequent runs skip **`POST`** when the labeled token already exists (leave existing file unchanged).
- [x] 7.3 `deploy/docker-compose.yml`: ensure `demo-stack-init` runs when **`with-agent`** is enabled (not only `with-console`); **`agent`** `depends_on` `demo-stack-init` **completed_successfully**; wire volume + `DEVAULT_AGENT_TOKEN` from file (or document override when operator sets env explicitly).
- [x] 7.4 Update `deploy/.env.stack.example`, `website/docs/admin/docker-compose.md` / quickstart: explain demo auto-token vs production (console / `deploy/iac/examples/curl-agent-token.sh`).
- [x] 7.5 Smoke: `make demo-stack-up` (or equivalent compose profiles) brings up **agent** without pre-exported `DEVAULT_AGENT_TOKEN` on the host when demo automation is enabled.

## 8. Website: Agent–control plane sequence diagrams

- [x] 8.1 In `website/docs/reference/grpc-services.md`, add a **Mermaid `sequenceDiagram`** covering **HTTP** `POST /api/v1/agent-tokens` (IAM JWT + `X-DeVault-Tenant-Id`), one-time `plaintext_secret`, and edge **`DEVAULT_AGENT_TOKEN`** configuration (no enrollment / no Redis session).
- [x] 8.2 In the same page (or adjacent subsection), add a **Mermaid `sequenceDiagram`** for **gRPC** steady state: **Register** (Bearer → `agent_tokens` / tenant → `edge_agents` snapshot + `agent_id`), **Heartbeat** (liveness + version gate), **LeaseJobs** (`bound_agent_id` narrowing), optional one-line reference to **RequestStorageGrant** / **CompleteJob** on the same Bearer path.
- [x] 8.3 Cross-link from `website/docs/admin/agent-fleet.md` (and optionally `openspec/.../design.md`) to the new section so readers discover the diagrams from fleet docs.

## 9. Changelog

- [x] 9.1 Append a consolidated entry under root **`CHANGELOG.md`** → **`[Unreleased]`** (appropriate **Added** / **Removed** / **Changed** / **Fixed** subsections per [Keep a Changelog](https://keepachangelog.com/)), summarizing the Agent token control-plane refactor, demo-stack HTTP bootstrap, website/docs updates, and migration ordering fix—style aligned with existing long-form bullets in this file.
