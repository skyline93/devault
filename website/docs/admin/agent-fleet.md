---
sidebar_position: 3
title: Agent 舰队与版本策略
description: edge_agents 登记、租户 enrollment、HTTP API、强制升级与 LeaseJobs 校验
---

# Agent 舰队与版本策略

控制面在每次成功的 **`Heartbeat`** 与 **`Register`** 后，将 Agent 标识与版本写入 PostgreSQL **`edge_agents`**（按 **`agent_id`** 去重更新），供运维查询舰队版本与自动化。

自迁移 **`0013`** 起，**`HeartbeatRequest.snapshot_schema_version >= 1`** 时还会持久化 **`hostname`**、**`host_os`**（API 字段 **`os`**）、**`region`**、**`agent_env`**（API **`env`**）与 **`backup_path_allowlist`**（JSON 数组）；详见 [gRPC（Agent）](../reference/grpc-services.md) 中 **Heartbeat 快照** 小节。

与 **gRPC 协议版本**的关系：`HeartbeatReply` / `RegisterReply` 中的 **`server_release`**、**`min_supported_agent_version`**、**`proto_package`** 以 **`proto/agent.proto`** 与 [gRPC（Agent）](../reference/grpc-services.md) 为准；本页侧重 **持久化登记**、**租户登记（enrollment）** 与 **`LeaseJobs`** 二次校验。

## 租户登记（enrollment，十四-01）

在 **`Register`** 能签发 **Redis gRPC Bearer** 之前，控制面必须在表 **`agent_enrollments`** 中为该 **`agent_id`** 配置至少一个 **`allowed_tenant_ids`**（租户 UUID 列表）。

| 方法 | 路径 | 说明 |
|------|------|------|
| **PUT** | `/api/v1/agents/{agent_id}/enrollment` | **admin**：创建或整表替换授权租户列表（请求体 **`allowed_tenant_ids`**，非空；租户须已存在）。 |
| **GET** | `/api/v1/agents/{agent_id}/enrollment` | 已认证主体读取当前登记。 |

**`Register`**：若缺少登记或列表为空 → **`FAILED_PRECONDITION`**（提示先 **`PUT .../enrollment`**）。

**`LeaseJobs` / 存储授权 / 完成**：对 **Register 会话** 以及 **带租户限制的 API Key**，仅允许 **`job.tenant_id`** ∈ 授权集合；与 REST **`allowed_tenant_ids`** 语义一致（见 [租户与 RBAC](./tenants-and-rbac.md)）。平台级 **`DEVAULT_API_TOKEN`**（未限制租户）仍可按既有方式运维全租户作业。

**Compose 演示**：迁移 **`0011`** 为固定 **`DEVAULT_AGENT_ID`**（默认 **`00000000-0000-4000-8000-000000000001`**）与 **`slug=default`** 租户写入一条种子登记；**`deploy/docker-compose.yml`** 中 **agent** 服务默认注入同一 **`DEVAULT_AGENT_ID`**。

## 跨租户隔离复核（十四-03，摘要）

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

- **全舰队**：路由 **`/execution/fleet`**（数据 **`GET /api/v1/agents`**）
- **租户内 Agent**：**`/execution/tenant-agents`**（**`GET /api/v1/tenant-agents`**；尚未 **Heartbeat** 的登记行也会列出，快照列可为空）
- **Agent 详情 / 登记 / 吊销**：**`/execution/fleet/:agentId`**

## HTTP API

需认证。**舰队列表不按 UI 租户 cookie 切片**（Agent 为平台级资源）；**登记写入**仅 **admin**。

| 方法 | 路径 | 说明 |
|------|------|------|
| **GET** | `/api/v1/agents` | 分页列出；**`limit`**（1–500）、**`offset`** |
| **GET** | `/api/v1/agents/{agent_id}` | 单条（含 **`allowed_tenant_ids`**，无登记时为 `null`） |
| **GET** | `/api/v1/agents/{agent_id}/enrollment` | 读取登记 |
| **PUT** | `/api/v1/agents/{agent_id}/enrollment` | **admin**：写入登记 |
| **POST** | `/api/v1/agents/{agent_id}/revoke-grpc-sessions` | **admin**：吊销 Register 签发 Redis Bearer |
| **GET** | `/api/v1/tenant-agents` | 列出 **当前有效租户**（**`X-DeVault-Tenant-Id`** 或默认 slug）下 **已登记** 的 Agent，并合并 **`edge_agents`** 快照（**`TenantScopedAgentOut`**） |

响应 **`EdgeAgentOut`** 含 **`meets_min_supported_version`**、**`proto_matches_control_plane`**、**`allowed_tenant_ids`**，以及 **`hostname`/`os`/`region`/`env`/`backup_path_allowlist`**（快照 v1 上报后）。

## 路径预检 Job（十四-11）

- **REST**：**`POST /api/v1/jobs/path-precheck`**，请求体 **`{"policy_id":"<uuid>"}`**（须对策略租户有写权限）。
- **语义**：入队 **`kind=path_precheck`** 作业；Agent **只读**检查策略 **`config.paths`** 在本地是否存在且可读，**不上传** bundle。结果写入 **`jobs.result_meta`**，**`schema`: `devault-path-precheck-report-v1`**（与 **`restore_drill`** 演练类 Job 区分）。
- **控制台**：**`/backup/precheck`** 入队预检；**`/backup/jobs`** 查看状态与 **`result_meta`**。
- **租约**：与备份相同策略绑定与租户过滤；**同一 `policy_id` 上活跃备份**仍通过 Redis 锁互斥，但 **pending 的 `path_precheck` 可与非备份活跃态并存**（SQL 候选仅将 **`kind=backup`** 视为阻塞同策略的其他 pending 作业）。

## 作业 hostname 快照（十四-12）

- **`jobs.lease_agent_hostname`**：在 **`LeaseJobs`** 成功将作业从 **`pending`→`running`** 时，从当时 **`edge_agents.hostname`** 写入（可为空）。
- **`jobs.completed_agent_hostname`**：**`CompleteJob`** 时优先取请求 **`agent_hostname`**（Agent 进程上报），否则回退 **`edge_agents.hostname`**。
- **REST / 控制台**：**`JobOut`** 与 **`/backup/jobs`** 表格展示 **`lease_agent_id`**、上述两列，便于审计（避免事后依赖可变 **`edge_agents`** 行）。

## 策略路径与 allowlist（十四-10）

- 租户字段 **`policy_paths_allowlist_mode`**：**`off`**（默认） | **`warn`**（路径越界时记日志仍保存） | **`enforce`**（**`400`** 拒绝创建/更新策略）。
- 校验对象：文件策略 **`config.paths`** 须落在 **本租户已登记 Agent** 在 **Heartbeat** 中上报的 **`backup_path_allowlist`** 之前缀**并集**之下（前缀匹配，与 Agent 侧 **`DEVAULT_ALLOWED_PATH_PREFIXES`** 对齐）。
- 若并集为空（尚无 Agent 上报 allowlist），**不执行**该校验，以免升级后阻断存量策略。

**REST**：**`PATCH /api/v1/tenants/{tenant_id}`**（admin）可更新 **`policy_paths_allowlist_mode`**；**控制台**：**`/platform/tenants`**（admin）。

**凭据吊销与轮换 Runbook**：[Agent 凭据生命周期](./agent-credential-lifecycle.md)。

## 策略执行绑定与 Agent 池（十四-05～07）

策略可设置 **`bound_agent_id`**（单 Agent）或 **`bound_agent_pool_id`**（池内任一成员，须 **enrollment** 覆盖租户）。**`LeaseJobs`** 在 SQL 层收窄候选作业，未绑定者 **无法** 领取对应 **`policy_id`** 的作业。同策略 **Redis 锁**、**租约过期** 与 **retry 新 job** 的语义见 [Agent 池与策略执行绑定](./agent-pools.md)。

## CLI

```bash
export DEVAULT_API_TOKEN=...
export DEVAULT_API_BASE_URL=http://127.0.0.1:8000
devault agent list
```

## 数据库

- 迁移 **`0007`** 创建 **`edge_agents`**：`first_seen_at`、`last_seen_at`、`agent_release`、`proto_package`、`git_commit`、`last_register_at` 等。  
- 迁移 **`0011`** 创建 **`agent_enrollments`**：`agent_id`（PK）、**`allowed_tenant_ids`**（JSONB UUID 字符串数组）、时间戳。

## 相关文档

- [兼容性与版本矩阵](../engineering/compatibility.md)
- [gRPC 与 API 多实例](./grpc-multi-instance.md)
- [租户与访问控制](./tenants-and-rbac.md)
