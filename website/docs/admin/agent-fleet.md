---
sidebar_position: 3
title: Agent 舰队与版本策略
description: edge_agents 登记、HTTP API、强制升级与 LeaseJobs 校验
---

# Agent 舰队与版本策略

控制面在每次成功的 **`Heartbeat`** 与 **`Register`** 后，将 Agent 标识与版本写入 PostgreSQL **`edge_agents`**（按 **`agent_id`** 去重更新），供运维查询舰队版本与自动化。

与 **gRPC 协议版本**的关系：`HeartbeatReply` / `RegisterReply` 中的 **`server_release`**、**`min_supported_agent_version`**、**`proto_package`** 以 **`proto/agent.proto`** 与 [gRPC（Agent）](../reference/grpc-services.md) 为准；本页侧重 **持久化登记** 与 **`LeaseJobs`** 二次校验。

## 强制升级（全局）

| 变量 | 作用 |
|------|------|
| **`DEVAULT_GRPC_MIN_SUPPORTED_AGENT_VERSION`** | 低于该 SemVer 的 **`agent_release`**：在 **`Heartbeat` / `Register`** 与（默认）**`LeaseJobs`** 上失败（`FAILED_PRECONDITION`），见 [配置参考](./configuration.md) 中 gRPC 版本策略。 |
| **`DEVAULT_GRPC_REQUIRE_AGENT_VERSION`** | 为 `true` 时，未上报 **`agent_release`** 的 Agent 被拒绝。 |
| **`DEVAULT_GRPC_ENFORCE_VERSION_ON_LEASE`** | 默认 **`true`**：`LeaseJobs` 根据 **`edge_agents`** 最近一次上报再次执行版本门闸；紧急演练时可置 `false`。 |

提高 **`DEVAULT_GRPC_MIN_SUPPORTED_AGENT_VERSION`** 可在滚动升级后切断过旧 Agent。

## Web 控制台

**HTTP Basic**，密码 **`DEVAULT_API_TOKEN`**（或 API Key 链）。

- 入口：**`/ui/agents`**
- 展示最近 **200** 条（按 **`last_seen_at`**），含 **`≥ min SemVer`**、**`Proto OK`**。

详见 [Web 控制台](../user/web-console.md)。

## HTTP API

需认证。**不按租户切片**（Agent 为平台级资源）。

| 方法 | 路径 | 说明 |
|------|------|------|
| **GET** | `/api/v1/agents` | 分页列出；**`limit`**（1–500）、**`offset`** |
| **GET** | `/api/v1/agents/{agent_id}` | 单条 |
| **POST** | `/api/v1/agents/{agent_id}/revoke-grpc-sessions` | **admin**：吊销 Register 签发 Redis Bearer |

响应 **`EdgeAgentOut`** 含 **`meets_min_supported_version`**、**`proto_matches_control_plane`**。

## CLI

```bash
export DEVAULT_API_TOKEN=...
export DEVAULT_API_BASE_URL=http://127.0.0.1:8000
devault agent list
```

## 数据库

迁移 **`0007`** 创建 **`edge_agents`**：`first_seen_at`、`last_seen_at`、`agent_release`、`proto_package`、`git_commit`、`last_register_at` 等。

## 相关文档

- [兼容性与版本矩阵](../engineering/compatibility.md)
- [gRPC 与 API 多实例](./grpc-multi-instance.md)
- [租户与访问控制](./tenants-and-rbac.md)
