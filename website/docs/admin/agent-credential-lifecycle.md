---
sidebar_position: 5
title: Agent 凭据吊销、轮换与泄露响应
description: Agent 令牌禁用、边端轮换、与运行中作业的影响（Runbook）
---

# Agent 凭据吊销、轮换与泄露响应

本文说明 **租户 Agent 令牌**（**`agent_tokens`**）与边端 **`DEVAULT_AGENT_TOKEN`** 的运维语义，与 REST **`POST /api/v1/agent-tokens/{id}/disable`** 及 gRPC 鉴权对齐。

## 凭据类型

| 类型 | 存储 / 绑定 | 典型用途 |
|------|----------------|----------|
| **租户 Agent 令牌** | DB **`token_hash`**；明文仅创建时返回 | 边端 **`DEVAULT_AGENT_TOKEN`**；**`Register`** 与全部 Agent gRPC |
| **`DEVAULT_API_TOKEN` / 控制面 API Key** | 环境或 DB 哈希 | 运维、CI、或 Agent 显式配置 **`DEVAULT_API_TOKEN`** 走 gRPC（受 API Key **`allowed_tenant_ids`** 约束） |

**`Register` 不再签发短期 Redis 会话**；吊销通过 **禁用令牌** 完成，无需 **`revoke-grpc-sessions`**。

## 吊销（立即失效）

**场景**：怀疑令牌泄露、主机失陷、或需强制下线使用该令牌的全部实例。

1. **禁用令牌**：**`POST /api/v1/agent-tokens/{token_id}/disable`**，或控制台 **执行组件 → Agent 令牌** 中禁用。  
   后续任意 gRPC 在鉴权阶段返回 **`UNAUTHENTICATED`**。
2. **运行中作业**：若 Agent 正持有租约，**后续** **`RequestStorageGrant` / `CompleteJob`** 会因令牌失效而失败；租约在 **`lease_expires_at`** 到达后由控制面回收为 **`pending`**。应在业务上预期 **该轮备份/恢复可能失败**，必要时人工 **retry** 或等待重新调度。
3. **不吊销 API Key**：控制面 API Key 使用 **`control_plane_api_keys`** 的禁用/轮换流程（见 [租户与 RBAC](./tenants-and-rbac.md)），与 Agent 令牌独立。

## 轮换（双窗 / 短暂重叠）

**目标**：在不停服的前提下更换边端 **`DEVAULT_AGENT_TOKEN`**。

**推荐顺序**：

1. 在控制台或 **`POST /api/v1/agent-tokens`** 创建 **新令牌**，保存一次性明文。  
2. 在目标主机更新 **`DEVAULT_AGENT_TOKEN`** 并重启 Agent；**`Register`** 可沿用本地 **`agent_id`** 或让控制面分配新实例。  
3. 确认 Heartbeat / LeaseJobs 正常后，**禁用旧令牌**。

同一令牌可绑定多台主机（多个 **`agent_id`**）；禁用令牌会同时切断其下全部实例。

## 泄露响应清单（摘要）

1. **禁用**泄露的 Agent 令牌。  
2. **审计**：检索 **`devault.grpc.audit`** 中 **`rpc`**、**`extra.agent_id`**、**`extra.job_id`**、**`extra.tenant_id`**。  
3. **复核舰队**：**`GET /api/v1/agents`** / **`GET /api/v1/tenant-agents`** 与策略 **`bound_agent_id`** 是否仍符合预期。  
4. 必要时 **新建令牌** 并滚动边端配置。

## 相关文档

- [Agent 舰队与版本策略](./agent-fleet.md)  
- [租户与 RBAC](./tenants-and-rbac.md)  
- [gRPC 服务参考](../reference/grpc-services.md)  
