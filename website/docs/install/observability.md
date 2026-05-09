---
sidebar_position: 5
title: 可观测性
description: Prometheus、健康检查与日志
---

# 可观测性

## Prometheus

控制面暴露 **`GET /metrics`**（Prometheus 文本格式）。本地 Compose 示例将 Prometheus 放在 **`deploy/docker-compose.prometheus.yml`**（与主栈叠加使用），抓取目标为 **`api:8000`**（见 `deploy/prometheus.yml`）。

常用排查步骤：

1. 确认 `api` 健康检查已通过
2. 浏览器或 `curl` 访问 `http://<host>:8000/metrics`
3. 在 Prometheus UI 中查询相关指标

与租户/访问控制相关的增量指标包括 **`devault_http_requests_total`**（`method`、`path_template`）与 **`devault_billing_committed_backup_bytes_total`**（`tenant_id`，备份成功提交时）；详见 [访问控制与 RBAC](../reference/access-control.md)。

## 健康检查

HTTP 层提供用于编排的就绪类端点（如 Compose 中使用的 **`/healthz`**）。部署时应将负载均衡/滚动更新与此类端点绑定。

## 版本信息

**`GET /version`** 返回 JSON，至少包含 **`service`**、**`version`**（与 `pyproject.toml` / `devault.__version__` 一致）、**`api`**（当前为 `v1`）、**`grpc_proto_package`**（如 `devault.agent.v1`）。若设置 **`DEVAULT_SERVER_GIT_SHA`**，则多一个 **`git_sha`** 字段。与 Agent 在 gRPC **Heartbeat** / **Register** 上交换的 `server_release` / `agent_release` 互补，便于发布校验与自动化探测。

## 日志

- 容器标准输出：由运行时收集（如 `docker compose logs -f api`）
- 生产建议接入集中日志（与基础设施一致）

## gRPC Health

Agent 侧依赖标准 gRPC Health 语义时，请参考 `proto` 与实现中的 health 服务注册方式（与 [gRPC 服务参考](../reference/grpc-services.md) 交叉阅读）。
