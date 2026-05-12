## ADDED Requirements

### Requirement: Mandatory policy bound agent

The control plane SHALL require `bound_agent_id` on policy create and update. The bound Agent SHALL belong to the same tenant as the policy via an `edge_agents` row linked to an Agent token for that tenant.

#### Scenario: Create policy without bound agent rejected

- **WHEN** a client attempts to create a policy without `bound_agent_id`
- **THEN** the API returns a validation error

#### Scenario: Bind to agent outside tenant rejected

- **WHEN** a client sets `bound_agent_id` to an instance whose token tenant does not match the policy tenant
- **THEN** the API returns a validation error

## REMOVED Requirements

### Requirement: Policy bound agent pool

**Reason**: Agent pools are removed; failover is out of scope for this execution model.

**Migration**: Replace pool bindings with explicit `bound_agent_id` per policy.

## MODIFIED Requirements

### Requirement: LeaseJobs policy filter

LeaseJobs candidate selection SHALL include only pending jobs whose associated policy’s `bound_agent_id` equals the leasing Agent’s `agent_id` when `job.policy_id` is present. Jobs for policies bound to a different Agent in the same tenant SHALL NOT be candidates. Tenant scope from the Agent token SHALL still apply.

#### Scenario: Same tenant different agent excluded

- **WHEN** agent B presents a valid token for tenant T and a pending job exists for tenant T on a policy bound to agent A
- **THEN** LeaseJobs for agent B does not return that job

#### Scenario: Matching agent receives job

- **WHEN** agent A presents a valid token for tenant T and a pending job exists for tenant T on a policy bound to agent A
- **THEN** LeaseJobs for agent A may lease the job subject to existing active-job and lock rules
