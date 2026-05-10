---
sidebar_position: 2
title: gRPC（Agent）
description: Agent RPC 与源码位置
---

# gRPC（Agent）

## 接口定义

**`proto/agent.proto`**

修改后：

```bash
bash scripts/gen_proto.sh
```

## 能力与入口

Agent 通过 gRPC **Register / Heartbeat / LeaseJobs / RequestStorageGrant / ReportProgress / CompleteJob** 等完成作业；详见 proto。

[gRPC](../trust/agent-connectivity.md)、[端口速查](./ports-and-paths.md)。

## Register 与会话令牌

**前提**：**`agent_enrollments`** 中已为该 **`agent_id`** 配置非空 **`allowed_tenant_ids`**（REST **`PUT /api/v1/agents/{agent_id}/enrollment`**，admin）。否则 **Register** → **`FAILED_PRECONDITION`**。

成功 **Register** 后控制面在 **Redis** 签发绑定 **`agent_id`** 的 **Bearer**，TTL **`DEVAULT_GRPC_AGENT_SESSION_TTL_SECONDS`**；RPC 成功后刷新 TTL。会话在控制面解析为 **`AuthContext.allowed_tenant_ids`**，与 **LeaseJobs / RequestStorageGrant / ReportProgress / CompleteJob** 的 **`job.tenant_id`** 硬过滤一致（与 **API Key** 的 **`allowed_tenant_ids`** 语义对齐）。**`LeaseJobs`** 另按策略 **`bound_agent_id` / `bound_agent_pool_id`** 收窄可领取的 **`policy_id`** 作业（见 [Agent 池](../admin/agent-pools.md)）。运维可用 **`POST /api/v1/agents/{agent_id}/revoke-grpc-sessions`** 吊销；Runbook 见 [Agent 凭据生命周期](../admin/agent-credential-lifecycle.md)。

## Heartbeat 快照（十四-08）

当 **`HeartbeatRequest.snapshot_schema_version >= 1`** 时，控制面将 **`hostname`**、**`os`**、**`region`**、**`env`** 与 **`backup_path_allowlist`**（绝对路径前缀列表）持久化到 **`edge_agents`**。**`snapshot_schema_version = 0`**（缺省）表示旧 Agent：不覆盖上述快照列，避免误清空。

- **Agent 侧**：同源 **`devault-agent`** 默认上报 **`snapshot_schema_version=1`**；**`backup_path_allowlist`** 来自 **`DEVAULT_ALLOWED_PATH_PREFIXES`**（逗号分隔，与 [配置参考](../admin/configuration.md) 中 Agent 小节一致）；**`region`/`env`** 可分别用 **`DEVAULT_AGENT_REGION`**、**`DEVAULT_AGENT_ENV`** 覆盖，否则 **`env`** 可回落到控制面 **`DEVAULT_ENV_NAME`** 类语义（见 Agent 代码）。
- **消费侧**：租户 **`policy_paths_allowlist_mode`** 与 **`GET /api/v1/tenant-agents`** / 策略 **`paths`** 校验见 [Agent 舰队](../admin/agent-fleet.md)。

## 版本协商

Agent 携带 **`agent_release`**、**`proto_package`**、**`git_commit`**；控制面返回 **`server_release`**、**`min_supported_agent_version`** 等。

| `devault-reason-code` | 典型 gRPC 状态 |
|-----------------------|----------------|
| `AGENT_VERSION_TOO_OLD` | `FAILED_PRECONDITION` |
| `AGENT_PROTO_PACKAGE_MISMATCH` | `FAILED_PRECONDITION` |
| `AGENT_VERSION_REQUIRED` | `FAILED_PRECONDITION` |
| `AGENT_REGISTRY_MISSING` | `FAILED_PRECONDITION`（LeaseJobs） |

详见 [租户与访问控制](../admin/tenants-and-rbac.md)（gRPC auditor 禁止）、[Agent 舰队](../admin/agent-fleet.md)。

### server_capabilities

**`HeartbeatReply`** / **`RegisterReply`** 带 **`server_capabilities`**（如 **`s3_presign_bundle`**、**`multipart_resume`**）；权威列表见仓库 **`docs/compatibility.json`** 与 [兼容性与版本矩阵](../engineering/compatibility.md)。

### CompleteJob 与恢复演练

**`CompleteJobRequest.agent_hostname`**：可选；控制面写入 **`jobs.completed_agent_hostname`**（审计）；未传时回退 **`edge_agents.hostname`**。

**`kind=restore_drill`** 时可填 **`result_summary_json`** → **`jobs.result_meta`**（见 [恢复演练](../user/restore-drill.md)）。**`kind=path_precheck`** 时同样通过 **`result_summary_json`** 上报 **`devault-path-precheck-report-v1`**（见 [Agent 舰队](../admin/agent-fleet.md) §路径预检）。

相关环境变量见 [配置参考](../admin/configuration.md) 中 gRPC 小节。
