## ADDED Requirements

### Requirement: Encrypt artifacts default for new policies

The console SHALL default `encrypt_artifacts` to enabled when the user starts creating a new policy. The user MAY turn it off before submit.

#### Scenario: New policy form initializes encryption on

- **WHEN** the user opens the new policy page with empty server-side policy state
- **THEN** the encrypt-artifacts control is enabled by default

#### Scenario: Edit existing policy does not force encryption default

- **WHEN** the user opens an existing policy for editing
- **THEN** the encrypt-artifacts control reflects the stored policy configuration

### Requirement: No policy enablement control on create or edit forms

The new-policy page and the edit-policy drawer SHALL NOT display a policy-level enabled/disabled switch. The create-policy request SHALL set `enabled` to true. The edit-policy PATCH from the drawer SHALL NOT send `enabled` unless a future change explicitly reintroduces enablement editing in the drawer.

#### Scenario: Create policy without enable switch

- **WHEN** the user submits the new policy form
- **THEN** the client sends enabled true and no enable switch was required on the form

#### Scenario: Edit drawer without enable switch

- **WHEN** the user edits a policy in the drawer
- **THEN** no policy-level enable switch is shown in the drawer

### Requirement: Policy-drawer backup schedule table actions

Inside the policy edit drawer, the embedded backup-schedule table SHALL NOT include a row link to external schedule-management pages (e.g. compliance schedule hub). The table SHALL NOT use a dedicated **Enabled** column. For authorized users, the **actions** column SHALL include a **Switch** bound to the schedule's `enabled` flag; changing the switch SHALL require secondary confirmation, then the client SHALL call `PATCH /api/v1/schedules/{schedule_id}` with the new `enabled` value and refresh the drawer schedule data on success. The actions column SHALL include an **Edit** control that opens a dialog to edit at least `cron_expression` and `timezone`, submitted via the same PATCH endpoint; the edit dialog SHALL NOT duplicate an enable switch (the actions-column Switch is the sole enablement control for writers). Delete schedule remains available per existing rules.

#### Scenario: Writer toggles schedule enablement from actions column

- **WHEN** a user with write access toggles a schedule's switch in the drawer table and confirms the dialog
- **THEN** the client PATCHes the schedule enabled field and the table reflects the updated state

#### Scenario: Writer edits cron and timezone

- **WHEN** a user with write access opens Edit on a schedule row, changes cron or timezone, and saves
- **THEN** the client PATCHes those fields and the row updates

#### Scenario: No plan-management link on schedule rows

- **WHEN** the drawer schedule table is rendered
- **THEN** there is no row action that navigates to external schedule management for that row's plan-management purpose

### Requirement: Agent hostname as user-visible identity in backup policy UI

Agent UUIDs (`bound_agent_id`, tenant agent `id`) SHALL remain internal binding values for API requests. The console backup policy list and policy create/edit flows SHALL present **hostnames** as the primary visible label: the policy list column titled per product copy (e.g. **Agent host**) SHALL render the bound agent's **hostname** resolved from tenant-scoped agent data, not the raw UUID as the main cell text. The policy bind `Select` SHALL show **hostname-only** option labels while keeping agent id as the form value; the console SHALL NOT show a prominent under-select link to the tenant-agents page for this purpose (per revised UX).

#### Scenario: Policy list shows hostname column

- **WHEN** the user views the backup policy list and a policy has `bound_agent_id` set
- **THEN** the Agent host column shows the matching agent hostname when available, not the UUID as the primary label

#### Scenario: Create policy select shows hostnames only

- **WHEN** the user opens the agent host selector on the new-policy page
- **THEN** each option label is the agent hostname (or defined fallback), and there is no tenant-agents shortcut link under the control

### Requirement: Execution fleet and tenant-agent tables use hostname and snapshot drawer

On the console **tenant agents** page and **fleet** (all agents) listing, the table SHALL NOT include a dedicated **Agent ID** column as primary scan text. The primary per-row identifier for users SHALL be **hostname** (or defined fallback). Clicking the hostname SHALL open a **right-side drawer** that presents the agent snapshot/detail content for that agent (reusing or factoring logic from the existing fleet detail view and its API calls).

#### Scenario: Tenant agents table without ID column

- **WHEN** a user opens the tenant agents list
- **THEN** there is no standalone agent-id column used as the main row label, and hostname is clickable to open the snapshot drawer

#### Scenario: Fleet table opens snapshot from hostname

- **WHEN** a user clicks a hostname in the fleet list
- **THEN** a right drawer opens with agent snapshot/detail for that agent

### Requirement: Backup jobs list columns and job detail drawer error

The backup jobs center table SHALL NOT include columns for **lease host** or **error message**. The column bound to the completion agent hostname (`completed_agent_hostname` or API equivalent) SHALL use product copy equivalent to **Agent host** (not "completion host" / "finish host"). When the user opens the **job detail drawer**, if the job has a non-empty error message, the drawer SHALL show that message in a dedicated readable section (multiline and copy-friendly as appropriate). The table SHALL NOT rely on an error column for primary triage.

#### Scenario: Jobs list without lease or error columns

- **WHEN** the user views the backup jobs list
- **THEN** there is no lease-host column, no error column, and the completion hostname appears under an Agent host titled column

#### Scenario: Job drawer shows error when present

- **WHEN** the user opens a job detail drawer and the job has a non-empty `error_message` (or equivalent field)
- **THEN** the drawer displays the error text in a dedicated section

### Requirement: Policy list created time as first column

The backup policy list table SHALL place **created time** (`created_at`) as the **first** column before policy name and the remaining columns.

#### Scenario: Policy list column order

- **WHEN** the user views the backup policy list
- **THEN** the first column is created time, followed by name and other columns

## MODIFIED Requirements

### Requirement: Single-page backup policy creation

The console backup policy creation flow SHALL present policy display name, file backup configuration, execution binding (`bound_agent_id`), and an optional single backup schedule on one scrollable page without requiring separate tabs or separate pages for these sections. The layout SHALL be compact: on typical desktop widths, related fields SHALL be arranged using a responsive grid (e.g. `Row`/`Col` or equivalent) so that associated controls can appear side-by-side and large blank right-side whitespace is avoided; on narrow viewports fields MAY stack vertically. Required fields SHALL remain obvious and optional sections clearly labeled. The form SHALL NOT include a policy-level enable switch; creation SHALL submit with enabled true.

#### Scenario: User creates policy without schedule on one page

- **WHEN** the user fills required fields for a new policy including execution binding and does not configure the optional schedule
- **THEN** the user can submit once from the same page and the policy is created enabled and without a schedule

#### Scenario: User creates policy with one optional schedule on one page

- **WHEN** the user fills required policy fields and completes the optional single schedule fields
- **THEN** the user can submit once from the same page and the system creates the enabled policy and exactly one associated schedule when the APIs require a policy id for schedule creation

### Requirement: Policy list enable toggle with confirmation

The policy list SHALL expose an enable/disable control per authorized row inside the **actions** column (alongside edit/delete and similar actions), not in a dedicated **Enabled** column. Read-only roles MAY see enablement as text or a Tag within the actions column or another compact presentation without a separate switch column. The control SHALL require a secondary confirmation before invoking the server update. If the user cancels confirmation, the UI SHALL remain unchanged. On successful update, the list SHALL refresh to reflect server state.

#### Scenario: Enable with confirmation from actions column

- **WHEN** the user attempts to enable a disabled policy using the control in the actions column
- **THEN** the console shows a confirmation dialog and only sends the enable update if the user confirms

#### Scenario: Cancel leaves state unchanged

- **WHEN** the user attempts to toggle enablement but cancels the confirmation
- **THEN** the row enablement display matches the prior server state

### Requirement: Edit policy in a right-side drawer with immutable paths and agent

The console SHALL open policy editing in a right-side drawer. In edit mode, backup path inputs and the bound agent selector SHALL be disabled and visually de-emphasized for all policy states (enabled or disabled). The drawer SHALL NOT include a policy-level enable/disable switch. After a successful save, the policy list SHALL refresh and the drawer SHALL remain open.

#### Scenario: Paths and agent are not editable in drawer

- **WHEN** the user edits an existing policy in the drawer
- **THEN** path fields and bound agent selection cannot be changed interactively

#### Scenario: Save keeps drawer open and refreshes list

- **WHEN** the user saves changes successfully from the drawer
- **THEN** the policy list data is refreshed and the drawer stays open
