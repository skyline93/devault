---
sidebar_position: 3
title: Agent 舰队与版本策略
description: Agent 令牌、edge_agents 登记、HTTP API、强制升级与 LeaseJobs 校验
---

# Agent 舰队与版本策略

控制面在每次成功的 **`Register`** 与 **`Heartbeat`** 后，将 Agent 实例标识与版本写入 PostgreSQL **`edge_agents`**（按 **`agent_id`** 去重更新），供运维查询舰队版本与自动化。

**`Register`** 携带主机快照（**`hostname`**、**`os`**、**`region`**、**`env`**、**`backup_path_allowlist`** 等）；**`Heartbeat`** 仅刷新存活时间与版本/proto 校验，不修改主机快照。详见 [gRPC（Agent）](../reference/grpc-services.md)（含 **重构后的 Mermaid 时序图**：HTTP 签发令牌与 Register / Heartbeat / LeaseJobs）。

与 **gRPC 协议版本**的关系：`HeartbeatReply` / `RegisterReply` 中的 **`server_release`**、**`min_supported_agent_version`**、**`proto_package`** 以 **`proto/agent.proto`** 与 [gRPC（Agent）](../reference/grpc-services.md) 为准（同页 **「时序概览（重构后）」** Mermaid 图）；本页侧重 **持久化登记**、**Agent 令牌** 与 **`LeaseJobs`** 二次校验。

## Agent 令牌（租户签发）

租户管理员在控制台 **执行组件 → Agent 令牌** 或 REST **`POST /api/v1/agent-tokens`** 创建长期凭据。库内仅存哈希；**明文仅在创建响应中出现一次**。边端 **`devault-agent`** 仅配置 **`DEVAULT_AGENT_TOKEN`**；**`Register`** 与后续 gRPC 均使用同一 Bearer，不经 IAM、不经 Redis 会话。

| 方法 | 路径 | 说明 |
|------|------|------|
| **POST** | `/api/v1/agent-tokens` | 创建令牌（响应含 **`plaintext_secret`**，仅一次）。 |
| **GET** | `/api/v1/agent-tokens` | 列出当前有效租户下的令牌（含 **`instance_count`**）。 |
| **GET** | `/api/v1/agent-tokens/{token_id}` | 单条元数据。 |
| **PATCH** | `/api/v1/agent-tokens/{token_id}` | 更新备注/描述。 |
| **POST** | `/api/v1/agent-tokens/{token_id}/disable` | 禁用令牌（已注册实例无法再通过 gRPC 鉴权）。 |
| **POST** | `/api/v1/agent-tokens/{token_id}/enable` | 重新启用。 |

**`Register`**：校验 Bearer 对应租户内未禁用、未过期的 **`agent_tokens`** 行；可携带可选 **`agent_id`**（否则由控制面分配）；写入或更新 **`edge_agents`** 快照并返回确认的 **`agent_id`**。同一令牌可对应多台 **`agent_id`** 实例（多主机各持久化本地 **`agent_instance.json`**）。

**`LeaseJobs` / 存储授权 / 完成**：Agent 令牌会话的租户由令牌行 **`tenant_id`** 固定；作业须属于该租户。每条策略 **必填 `bound_agent_id`**；**`LeaseJobs`** 在 SQL 层仅返回绑定到当前 **`agent_id`** 的策略作业。

## 跨租户隔离复核（摘要）

- **S3 键**：文件插件 **`artifact_object_keys`** 含 **`tenants/<tenant_id>/artifacts/<job_id>`**，与 **`job.tenant_id`** 一致。  
- **预签名**：仅针对上述键或已租约作业关联的 **restore** artifact。  
- **指标**：**`devault_jobs_total`**、**`devault_billing_committed_backup_bytes_total`** 等已带 **`tenant_id`**（或作业级标签）。  
- **审计**：**`devault.grpc.audit`** 在 **`RequestStorageGrant`** / **`CompleteJob`** 等路径的 **`extra`** 中带 **`tenant_id`**（字符串 UUID），不含密钥。

## 强制升级（全局）

| 变量 | 作用 |
|------|------|
| **`DEVAULT_GRPC_MIN_SUPPORTED_AGENT_VERSION`** | 低于该 SemVer 的 **`agent_release`**：在 **`Heartbeat` / `Register`** 与（默认）**`LeaseJobs`** 上失败（`FAILED_PRECONDITION`），见 [配置参考](./configuration.md) 中 gRPC 版本策略。 |
| **`DEVAULT_GRPC_REQUIRE_AGENT_VERSION`** | 为 `true` 时，未上报 **`agent_release`** 的 Agent 被拒绝。 |
| **`DEVAULT_GRPC_ENFORCE_VERSION_ON_LEASE`** | 默认 **`true`**：`LeaseJobs` 根据 **`edge_agents`** 最近一次上报再次执行版本门闸；紧急演练时可置 `false`。 |

提高 **`DEVAULT_GRPC_MIN_SUPPORTED_AGENT_VERSION`** 可在滚动升级后切断过旧 Agent。

## Web 控制台（`console/`）

Bearer 与 REST 一致（见 [Web 控制台](../user/web-console.md)）。

- **Agent 令牌**：**`/execution/agent-tokens`**
- **全舰队**：**`/execution/fleet`**（**`GET /api/v1/agents`**）
- **租户内 Agent**：**`/execution/tenant-agents`**（**`GET /api/v1/tenant-agents`**）
- **Agent 详情**：**`/execution/fleet/:agentId`**

## HTTP API

需认证。**舰队列表不按 UI 租户 cookie 切片**（Agent 为平台级资源）；**令牌写入**须对目标租户有写权限。

| 方法 | 路径 | 说明 |
|------|------|------|
| **GET** | `/api/v1/agents` | 分页列出；**`limit`**（1–500）、**`offset`** |
| **GET** | `/api/v1/agents/{agent_id}` | 单条注册实例（含 **`agent_token_id`** 与主机快照） |
| **GET** | `/api/v1/tenant-agents` | 列出 **当前有效租户** 下已注册实例，并合并 **`edge_agents`** 快照（**`TenantScopedAgentOut`**） |

响应 **`EdgeAgentOut`** 含 **`meets_min_supported_version`**、**`proto_matches_control_plane`**，以及 **`hostname`/`os`/`region`/`env`/`backup_path_allowlist`**（**Register** 上报后）。

## 路径预检 Job

- **REST**：**`POST /api/v1/jobs/path-precheck`**，请求体 **`{"policy_id":"<uuid>"}`**（须对策略租户有写权限）。
- **语义**：入队 **`kind=path_precheck`** 作业；Agent **只读**检查策略 **`config.paths`** 在本地是否存在且可读，**不上传** bundle。结果写入 **`jobs.result_meta`**，**`schema`: `devault-path-precheck-report-v1`**。
- **控制台**：**`/backup/precheck`** 入队预检；**`/backup/jobs`** 查看状态与 **`result_meta`**。

## 作业 hostname 快照

- **`jobs.lease_agent_hostname`**：在 **`LeaseJobs`** 成功将作业从 **`pending`→`running`** 时，从当时 **`edge_agents.hostname`** 写入（可为空）。
- **`jobs.completed_agent_hostname`**：**`CompleteJob`** 时优先取请求 **`agent_hostname`**（Agent 进程上报），否则回退 **`edge_agents.hostname`**。
- **REST / 控制台**：**`JobOut`** 与 **`/backup/jobs`** 表格展示 **`lease_agent_id`**、上述两列，便于审计。

## 策略路径与 allowlist

- 租户字段 **`policy_paths_allowlist_mode`**：**`off`**（默认） | **`warn`** | **`enforce`**。
- 校验对象：文件策略 **`config.paths`** 须落在 **本租户已注册 Agent** 在 **Register** 中上报的 **`backup_path_allowlist`** 之前缀**并集**之下。
- 若并集为空，**不执行**该校验，以免升级后阻断存量策略。

**凭据吊销与轮换 Runbook**：[Agent 凭据生命周期](./agent-credential-lifecycle.md)。

## 策略执行绑定

策略 **必填 `bound_agent_id`**（须为本租户下已通过该租户令牌 **Register** 的 **`agent_id`**）。**`LeaseJobs`** 在 SQL 层收窄候选作业；同策略 **Redis 锁**、**租约过期** 与 **retry 新 job** 语义不变。历史 **Agent 池** 已移除，见 [Agent 池（已下线）](./agent-pools.md)。

## CLI

```bash
export DEVAULT_API_TOKEN=...
export DEVAULT_API_BASE_URL=http://127.0.0.1:8000
devault agent list
```

## 数据库

- **`edge_agents`**：实例 **`id`**、**`agent_token_id`**、版本与主机快照、**`first_seen_at` / `last_seen_at` / `last_register_at`** 等。  
- **`agent_tokens`**：租户 FK、**`token_hash`**、备注、**`expires_at` / `disabled_at`**、**`last_used_at`**。

## 相关文档

- [兼容性与版本矩阵](../engineering/compatibility.md)
- [gRPC 与 API 多实例](./grpc-multi-instance.md)
- [租户与访问控制](./tenants-and-rbac.md)
