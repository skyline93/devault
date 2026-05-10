---
sidebar_position: 7
title: Agent 池与策略执行绑定
description: agent_pools、成员、权重/排序与 LeaseJobs 收窄（§十四 05–07）
---

# Agent 池与策略执行绑定

对应企业待办 **十四-05～十四-07**：策略可绑定 **单台 Agent**（`policies.bound_agent_id`）或 **Agent 池**（`policies.bound_agent_pool_id`）；**`LeaseJobs`** 仅返回当前 Agent **有权领取**的待办作业；同策略 **Redis 互斥锁** 与 **租约过期回收** 与池内 **failover** 组合行为见下文。

## 数据模型

| 表 | 作用 |
|----|------|
| **`agent_pools`** | 租户内命名池（`tenant_id` + `name`）。 |
| **`agent_pool_members`** | `pool_id` + `agent_id`，可选 **`weight`**（默认 100，预留给后续加权调度）、**`sort_order`**（默认 0；**越小越靠前**，文档上可作主备/优先级说明）。 |
| **`policies`** | 可选 **`bound_agent_id`** 或 **`bound_agent_pool_id`**（**互斥**，数据库 CHECK）。 |

成员 **Agent** 必须在 **`agent_enrollments`** 中包含该池所在 **租户**（与单 Agent 绑定校验一致）。

## REST API

前缀 **`/api/v1/agent-pools`**（需认证；租户来自 **`X-DeVault-Tenant-Id`** / 默认租户）。

| 方法 | 路径 | 说明 |
|------|------|------|
| **POST** | `/agent-pools` | 创建池（body：`name`）。 |
| **GET** | `/agent-pools` | 列出当前租户池。 |
| **GET** | `/agent-pools/{id}` | 池详情 + 成员 + 各成员 **`last_seen_at`**（来自 **`edge_agents`**，作健康快照）。 |
| **PUT** | `/agent-pools/{id}/members` | **整表替换**成员列表（body：`members: [{agent_id, weight?, sort_order?}]`）。 |
| **DELETE** | `/agent-pools/{id}` | 删除池；本租户下引用该池的策略 **`bound_agent_pool_id`** 置空。 |

策略侧使用 **`PATCH /api/v1/policies/{id}`**（或创建时字段）设置 **`bound_agent_id`** 或 **`bound_agent_pool_id`**。

## `LeaseJobs` 行为（十四-05）

- 作业 **`policy_id` 为空**（内联配置备份）：不施加执行绑定过滤。  
- 策略 **未绑定**：任意满足 **租户 enrollment** 的 Agent 可领。  
- **`bound_agent_id`**：仅该 **`agent_id`** 可领该策略作业。  
- **`bound_agent_pool_id`**：仅 **池成员** 可领。

与 **十四-02** 的 **`allowed_tenant_ids`** 为 **与** 关系：Agent 必须 **同时** 满足租户 enrollment 与策略绑定。

## 调度、锁与池内 failover（十四-07）

1. **同策略并发**：与既有实现一致，**同一 `policy_id` 的备份**在 Redis 中 **互斥**（`devault:policy-lock:<policy_id>`），任意时刻 **至多一个** RUNNING/UPLOADING/VERIFYING 作业持有锁。  
2. **租约过期**：`lease_expires_at` 到期后控制面将作业置回 **`pending`** 并释放 Redis 锁（若仍持有）；**池内另一台**已注册且满足 enrollment 的 Agent 可在下次 **`LeaseJobs`** 抢到该作业。  
3. **失败重试**：API **retry** 产生 **新 `job_id`** 的新 **`pending`** 作业；**任意合格池成员**均可领取（仍受绑定与 enrollment 约束）。  
4. **sort_order / weight**：当前 **不在控制面**做加权随机派发；**拉取顺序**仍为作业 **`created_at` FIFO**。**`sort_order`** 用于文档与 UI 列表顺序，便于运维标注「主 / 备」；**`weight`** 预留给后续调度增强。

## Web 控制台（`console/`）

- **`/execution/agent-pools`**、**`/execution/agent-pools/:poolId`**：列表、成员编辑、删除。  
- **策略**（**`/backup/policies/new`**、**`…/edit`**）：执行绑定模式 + Agent 或池下拉。

## 相关文档

- [Agent 舰队与版本策略](./agent-fleet.md)  
- [Agent 凭据生命周期](./agent-credential-lifecycle.md)  
- [gRPC（Agent）](../reference/grpc-services.md)  
