---
sidebar_position: 1
title: Agent 连接
description: gRPC 拓扑与生产部署要点
---

# Agent 连接

## 默认模型

- Agent 通过 **`DEVAULT_GRPC_TARGET`** 连接控制面 gRPC 监听地址（Compose 内常为 `api:50051`）。
- HTTP API 与 gRPC 可在同一 **api** 进程内共存，由 `DEVAULT_GRPC_LISTEN` 控制是否监听。

## 生产拓扑

常见模式：

1. **内网明文 gRPC**：仅当网络边界可信时使用。
2. **TLS 在网关终结**：Agent → Envoy/Nginx（TLS）→ 内网明文 gRPC → `api`。仓库提供叠加 Compose 与证书生成脚本示例（见 [TLS 与网关](./tls-and-gateway.md)）。

## 防火墙与安全组

放行：

- Agent → gRPC 端口（默认 **50051**，或网关对外端口如 **50052**）
- Agent → S3 端点（与预签名中的主机一致）
- 控制面 → PostgreSQL / Redis（不对 Agent 暴露）

## 注册与身份

具体 RPC（如 Register、租约拉取）以仓库内 **`proto/agent.proto`** 为准；令牌类配置见 [API 访问控制](./api-access.md)。**Heartbeat** 与 **Register** 上的发行版 / proto 包协商与运维可调策略见 [gRPC 服务参考](../reference/grpc-services.md) 与 [配置参考](../install/configuration.md)。
