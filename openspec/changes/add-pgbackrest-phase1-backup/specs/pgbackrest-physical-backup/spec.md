## ADDED Requirements

### Requirement: Physical backup policy configuration

The system SHALL allow a tenant policy with `plugin` set to the physical backup plugin identifier (`postgres_pgbackrest` unless renamed in implementation) and a versioned JSON `config` that includes at least: `stanza`, PostgreSQL endpoint fields (`pg_host`, `pg_port`), `pg_data_path` (path string on the database server for pgBackRest metadata), repository targeting fields that exclude long-lived secrets (for example bucket name, object prefix, region identifier), `pgbackrest_operation` with allowed values `backup` or `expire` (defaulting to `backup` when omitted), and when `pgbackrest_operation` is `backup` a backup mode field (`full` or `incr`, exact field name as chosen in implementation). When `pgbackrest_operation` is `expire`, a backup mode field MUST NOT be required. The system MUST reject persistence of database passwords, static cloud secret keys, or other high-sensitivity material inside `policies.config` / `jobs.config_snapshot` JSON.

#### Scenario: Valid policy accepted

- **WHEN** a tenant administrator creates or updates a policy with `plugin` set to the physical backup identifier and `config` contains only allowed non-secret fields
- **THEN** the policy is stored and subsequent backup jobs MAY reference it

#### Scenario: Secret material rejected

- **WHEN** a policy or inline backup config includes a forbidden secret field name or pattern defined by server-side validation
- **THEN** the API returns a client error and no policy or job snapshot is persisted with that secret material

#### Scenario: Expire policy without backup mode

- **WHEN** a policy uses the physical backup plugin with `pgbackrest_operation=expire` and omits backup mode fields
- **THEN** validation succeeds and schedules MAY enqueue expire maintenance jobs

### Requirement: Enqueue physical backup jobs

The system SHALL accept `POST /api/v1/jobs/backup` requests that enqueue a `BACKUP` job for the physical backup plugin using either `policy_id` or an inline config that passes the same validation rules as policies. Scheduled jobs SHALL be enqueued using the policy's `plugin` and full `config` snapshot (including `pgbackrest_operation`) consistent with the scheduler implementation for file backups, so that schedules linked to expire-only physical policies produce expire jobs without a separate scheduler entrypoint.

#### Scenario: Manual backup enqueued

- **WHEN** an authorized client submits a valid backup job body with `plugin` set to the physical backup identifier
- **THEN** a `PENDING` job row exists and is eligible for edge Agent leasing according to tenant and agent binding rules

### Requirement: Tenant may mix file and physical backup policies

The system SHALL NOT prohibit a tenant from owning multiple enabled policies where some use `plugin=file` and others use the physical backup plugin identifier, beyond normal per-policy validation and quota policies if any exist.

#### Scenario: Two plugins in one tenant

- **WHEN** a tenant creates one enabled file policy and one enabled physical-backup policy
- **THEN** both policies persist and either may receive schedules or manual backup jobs independently

### Requirement: Scheduled pgBackRest expire jobs

The system SHALL enqueue `BACKUP` jobs for the physical backup plugin when a linked `Schedule` fires for a policy whose configuration indicates `pgbackrest_operation=expire`, using the same scheduling pipeline as other policy-driven backup jobs. An edge Agent SHALL execute `pgbackrest expire` with a fixed argument vector for such jobs. Successful completion SHALL follow the same control-plane completion rules as physical `backup` jobs: no file `artifacts`, structured summary persisted to `result_meta` from `result_summary_json`.

#### Scenario: Scheduled expire enqueued

- **WHEN** a cron schedule triggers for a policy with the physical backup plugin and `pgbackrest_operation=expire`
- **THEN** a `PENDING` `BACKUP` job is created whose snapshot includes expire operation and is eligible for leasing by the bound Agent

#### Scenario: Expire completes without artifact

- **WHEN** the Agent completes `pgbackrest expire` successfully with valid structured summary
- **THEN** the job reaches `SUCCESS` with `result_meta` populated and no `artifacts` row is created

### Requirement: Edge Agent executes pgBackRest backup or expire

An edge Agent that has leased a `BACKUP` job for the physical backup plugin SHALL read `pgbackrest_operation` from the leased job snapshot (default `backup`). When the operation is `backup`, the Agent SHALL execute `pgbackrest backup` with `--type` matching the configured mode (`full` or `incr`). When the operation is `expire`, the Agent SHALL execute `pgbackrest expire` with a fixed argument vector. In all cases the Agent SHALL use a fixed argument vector without shell interpolation of user-controlled strings, derive non-secret configuration from the snapshot, resolve secrets only through approved local channels, and send `CompleteJob` with structured `result_summary_json` on success or `error_code` / `error_message` on failure.

#### Scenario: Successful backup completion

- **WHEN** `pgbackrest backup` exits zero and optional info collection succeeds
- **THEN** the Agent calls `CompleteJob` with `success=true` and non-empty structured `result_summary_json`

#### Scenario: Successful expire completion

- **WHEN** `pgbackrest expire` exits zero and optional info collection succeeds
- **THEN** the Agent calls `CompleteJob` with `success=true` and non-empty structured `result_summary_json`

#### Scenario: Failed backup completion

- **WHEN** `pgbackrest backup` exits non-zero or times out
- **THEN** the Agent calls `CompleteJob` with `success=false` and populated `error_code` / `error_message` suitable for operators

#### Scenario: Failed expire completion

- **WHEN** `pgbackrest expire` exits non-zero or times out
- **THEN** the Agent calls `CompleteJob` with `success=false` and populated `error_code` / `error_message` suitable for operators

### Requirement: Control plane completes physical backup without file artifacts

On `CompleteJob` for a successful `BACKUP` job whose `plugin` is the physical backup identifier (including jobs that ran `pgbackrest expire`), the control plane SHALL NOT require `bundle_key` or `manifest_key`, SHALL NOT read a DeVault file-plugin manifest from object storage for integrity of this job, and SHALL NOT insert an `artifacts` row for this completion path. The control plane SHALL persist the structured summary from `result_summary_json` into `jobs.result_meta` (or an approved equivalent first-class column agreed in implementation) and SHALL set the job status to `SUCCESS` with timestamps consistent with other job kinds.

#### Scenario: Success without artifact keys

- **WHEN** `CompleteJob` reports `success=true` for a physical backup job and `result_summary_json` parses as an object
- **THEN** no `artifacts` row is created for that job and `result_meta` contains the parsed summary

#### Scenario: Reject file-style completion for physical plugin

- **WHEN** `CompleteJob` reports `success=true` for a physical backup job but omits required summary fields defined by validation
- **THEN** the control plane rejects the completion with an appropriate error and the job does not enter `SUCCESS`

### Requirement: API and console visibility

The OpenAPI description and generated console types SHALL include the extended backup job and policy shapes for the physical backup plugin. The console SHALL provide a minimal path to create or attach a physical-backup policy and to view backup jobs with `result_meta` visible in the job detail view (or dedicated panel), without advertising file-artifact download for this plugin.

#### Scenario: Job detail shows summary

- **WHEN** a user opens a succeeded physical backup job in the console
- **THEN** the UI displays key fields from `result_meta` (for example stanza and backup type) and does not show a file download action tied to `artifacts` for this job

### Requirement: Observability labels

Prometheus metrics that include `plugin` as a label for job duration or terminal counts SHALL use the actual job `plugin` string for physical backup jobs, not a hard-coded `file` label.

#### Scenario: Metric label matches plugin

- **WHEN** a physical backup job reaches a terminal state
- **THEN** emitted metrics use `plugin=postgres_pgbackrest` (or the chosen identifier) consistently for that job's labels

### Requirement: Demo stack provides PostgreSQL target and pgBackRest-capable Agent

The repository's documented Docker Compose demo stack (including the profiles used by `make demo-stack-up` when agents are enabled) SHALL include a PostgreSQL service that is **not** the control-plane metadata database, intended solely as the **backup target** for pgBackRest validation (`pg_host`, `pg_port`, `pg_data_path` in demo policies refer to this service). Edge Agent services (`agent` / `agent2`) SHALL use an image built from the shared `deploy/Dockerfile` **extended to install the `pgbackrest` CLI** (demo stack decision: single image, no separate agent-only Dockerfile required). The Agent SHALL reach the target PostgreSQL and MinIO on the compose network; S3 credentials for pgBackRest SHALL be supplied via **Agent environment variables** (not policy JSON). Operator-facing documentation SHALL list service DNS names, example `stanza`, repo prefix conventions, and required env vars for a successful **FULL** and optional **expire** smoke run.

#### Scenario: Demo target Postgres is reachable from Agent

- **WHEN** the demo stack is up with the physical-backup profile enabled
- **THEN** the pgBackRest-capable Agent container can open a TCP connection to the documented `pg_host:pg_port` of the target PostgreSQL service

#### Scenario: Smoke backup without external Patroni

- **WHEN** an operator follows the demo documentation to enqueue one `postgres_pgbackrest` backup job against the bundled target PostgreSQL and MinIO repo
- **THEN** the job can reach `SUCCESS` with `result_meta` populated without requiring an external Patroni cluster
