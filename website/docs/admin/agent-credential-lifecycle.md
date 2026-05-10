---
sidebar_position: 5
title: Agent 凭据吊销、轮换与泄露响应
description: Register 会话、登记变更、与运行中作业的影响（Runbook）
---

# Agent 凭据吊销、轮换与泄露响应

本文对应企业待办 **十四-04**，与 **§十四 · 十四-01**（登记）、**一-09**（Redis 会话）及 REST **`POST /api/v1/agents/{id}/revoke-grpc-sessions`** 对齐。

## 凭据类型

| 类型 | 存储 / 绑定 | 典型用途 |
|------|----------------|----------|
| **Register 签发的 gRPC Bearer** | Redis **`devault:grpc:sess:*`**，载荷绑定 **`agent_id`** + 代际 **`v`** | Agent 无 **`DEVAULT_API_TOKEN`** 时的默认路径 |
| **`DEVAULT_API_TOKEN` / 控制面 API Key** | 环境或 DB 哈希 | 运维、CI、或 Agent 显式配置 **`DEVAULT_API_TOKEN`** 走 gRPC（受 API Key **`allowed_tenant_ids`** 约束） |
| **`DEVAULT_GRPC_REGISTRATION_SECRET`** | 控制面 + Agent 环境 | **仅**用于 **`Register`** 首跳，**不是**会话令牌 |

## 吊销（立即失效）

**场景**：怀疑 Register 会话泄露、主机失陷、或需强制下线某台 Agent。

1. **调用吊销**（admin）：**`POST /api/v1/agents/{agent_id}/revoke-grpc-sessions`**，或 Web **`/ui/agents`** 行内 **Revoke gRPC sessions**。  
   实现为 Redis **`INCR devault:grpc:sess_ver:{agent_id}`**；所有旧会话载荷中的 **`v`** 与当前代际不一致，**下一次任意 gRPC** 即 **`UNAUTHENTICATED`**。
2. **运行中作业**：若 Agent 正持有租约，**后续** **`RequestStorageGrant` / `CompleteJob`** 会因令牌失效而失败；租约在 **`lease_expires_at`** 到达后由控制面回收为 **`pending`**（与既有租约语义一致）。应在业务上预期 **该轮备份/恢复可能失败**，必要时人工 **retry** 或等待重新调度。
3. **不吊销 API Key**：吊销 API Key 使用 **`control_plane_api_keys`** 的禁用/轮换流程（见 [租户与 RBAC](./tenants-and-rbac.md)），与 Register 会话独立。

## 轮换（双窗 / 短暂重叠）

**目标**：在不停服的前提下更新 Register 依赖的 **`DEVAULT_GRPC_REGISTRATION_SECRET`** 或迁移到新 **`DEVAULT_AGENT_ID`**。

**推荐顺序**：

1. **保持旧 Agent 进程运行**，先在控制面为 **新 `agent_id`** 写入 **`PUT .../enrollment`**（若切新 UUID），或保留同一 **`agent_id`** 仅更新 **`allowed_tenant_ids`**。
2. **部署新 `DEVAULT_GRPC_REGISTRATION_SECRET`** 到控制面与 Agent（同一值），**重启 Agent**；首跳 **`Register`** 领取新 Redis Bearer。
3. **确认** Heartbeat / LeaseJobs 正常后，**吊销旧会话**（若曾短期保留旧 secret，应在全部实例升级后撤销旧 secret 并执行一次 **revoke** 以清理仍缓存在内存中的旧 Bearer）。

同一 **`agent_id`** 下 **不建议**长期并行两套有效 Register 会话；代际吊销是 **整 Agent** 粒度。

## 租户授权变更

**`PUT /api/v1/agents/{agent_id}/enrollment`** 替换 **`allowed_tenant_ids`** 后：

- **不**自动吊销 Redis 会话；已持有 Bearer 的 Agent 仍可能通过 **`Heartbeat`** 刷新 TTL，但 **仅能领租** **`job.tenant_id`** 属于新列表的作业。  
- 若需 **立即**切断：在 **`PUT` 成功后执行 `revoke-grpc-sessions`**，强制其 **`Register`** 并重新加载本地状态。

## 泄露响应清单（摘要）

1. **吊销**该 Agent 的 Register 会话（上节）。  
2. **轮换** **`DEVAULT_GRPC_REGISTRATION_SECRET`**（若泄露的是注册密钥）。  
3. **审计**：检索 **`devault.grpc.audit`**（JSON）中 **`rpc`**、**`extra.agent_id`**、**`extra.job_id`**、**`extra.tenant_id`**（存储授权与完成路径已带租户，便于按租户排障）。  
4. **复核登记**：**`GET /api/v1/agents/{agent_id}/enrollment`** 与 **`GET /api/v1/agents/{agent_id}`** 的 **`allowed_tenant_ids`** 是否与策略租户一致。

## 相关文档

- [Agent 舰队与版本策略](./agent-fleet.md)  
- [租户与 RBAC](./tenants-and-rbac.md)  
- [gRPC 服务参考](../reference/grpc-services.md)  
