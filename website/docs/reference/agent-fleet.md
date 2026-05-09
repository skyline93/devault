---
sidebar_position: 5
title: Agent 批量管理与版本策略
description: edge_agents 登记、HTTP 查询、强制升级与 LeaseJobs 校验
---

# Agent 批量管理与版本策略

控制面在每次成功的 **`Heartbeat`** 与 **`Register`** 后，将 Agent 标识与版本写入 PostgreSQL 表 **`edge_agents`**（按 **`agent_id`** 去重更新），供运维 **查询舰队版本**、审计与自动化。

与 **gRPC 协议版本**的关系：`HeartbeatReply` / `RegisterReply` 中的 **`server_release`**、**`min_supported_agent_version`**、**`proto_package`** 语义仍由 **`proto/agent.proto`** 与 [`gRPC 服务参考](./grpc-services.md) 定义；本页侧重 **持久化登记** 与 **`LeaseJobs`** 侧的二次校验。

---

## 强制升级（全局）

以下环境变量共同约束 Agent，无需逐台配置：

| 变量 | 作用 |
|------|------|
| **`DEVAULT_GRPC_MIN_SUPPORTED_AGENT_VERSION`** | 低于该 SemVer 的 **`agent_release`**：在 **`Heartbeat` / `Register`** 与（默认）**`LeaseJobs`** 上失败（`FAILED_PRECONDITION`），见 [配置参考](../install/configuration.md#ggrpc-版本策略控制面）。 |
| **`DEVAULT_GRPC_REQUIRE_AGENT_VERSION`** | 为 `true` 时，未上报 **`agent_release`** 的 Agent 被拒绝。 |
| **`DEVAULT_GRPC_ENFORCE_VERSION_ON_LEASE`** | 默认 **`true`**：`LeaseJobs` 根据 **`edge_agents`** 中最近一次上报的版本/proto **再次**执行与 Heartbeat 相同的门闸（防止绕过心跳路径）；仅在故障演练或迁移窗口内置 `false`。 |

将 **`DEVAULT_GRPC_MIN_SUPPORTED_AGENT_VERSION`** 提高到新版本底线，即可在滚动升级完成后 **切断过旧 Agent**（批量强制升级）。

---

## 简易 Web UI

与 Jobs / Artifacts 相同认证：**HTTP Basic**，密码为 **`DEVAULT_API_TOKEN`**（或与 **`control_plane_api_keys`** 一致的密钥）。

- 入口：**`/ui/agents`**（本地示例 `http://127.0.0.1:8000/ui/agents`）
- 展示最近 **200** 条（按 **`last_seen_at`** 降序），含 **`≥ min SemVer`**、**`Proto OK`** 列。

详见 [简易 Web UI](../guides/web-console.md)。

---

## HTTP API：舰队清单

需认证（Bearer / API Key / OIDC），**不按租户切片**（Agent 为平台级资源）。

| 方法 | 路径 | 说明 |
|------|------|------|
| **GET** | `/api/v1/agents` | 分页列出 Agent（默认按 **`last_seen_at`** 降序）；查询参数 **`limit`**（1–500）、**`offset`**。 |
| **GET** | `/api/v1/agents/{agent_id}` | 按 UUID 返回单条记录。 |

响应模型 **`EdgeAgentOut`** 含 **`meets_min_supported_version`**、**`proto_matches_control_plane`**，便于仪表盘一眼识别不合规实例。

---

## CLI

```bash
export DEVAULT_API_TOKEN=...
export DEVAULT_API_BASE_URL=http://127.0.0.1:8000   # 可选
devault agent list
```

---

## 数据库

迁移 **`0007`**（文件 **`alembic/versions/20260509_0007_edge_agents.py`**）创建 **`edge_agents`**，字段包括 **`first_seen_at`**、**`last_seen_at`**、**`agent_release`**、**`proto_package`**、**`git_commit`**、**`last_register_at`**。

---

## 相关文档

- [兼容性与版本矩阵](../development/compatibility.md)
- [gRPC 与 API 多实例部署](../install/grpc-multi-instance.md)
- [访问控制与 RBAC](./access-control.md)
