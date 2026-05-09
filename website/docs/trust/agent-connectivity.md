---
sidebar_position: 3
title: Agent 连接
description: gRPC 拓扑与生产部署要点
---

# Agent 连接

## 默认模型

- Agent 通过 **`DEVAULT_GRPC_TARGET`** 连接控制面 gRPC。
- HTTP 与 gRPC 可在同一 **api** 进程，`DEVAULT_GRPC_LISTEN` 控制监听。

## 生产拓扑

1. **内网明文 gRPC**：仅当边界绝对可信。
2. **TLS 在网关终结**：Agent → Envoy/Nginx（TLS）→ 内网明文 gRPC → `api`（见 [TLS 与网关](./tls-and-gateway.md)）。

## 防火墙与安全组

放行：

- Agent → gRPC（默认 **50051** 或网关 **50052** 等）
- Agent → S3 端点（与预签名主机一致）
- 控制面 → PostgreSQL / Redis（不对 Agent 暴露）

## 注册与身份

RPC 定义见 **`proto/agent.proto`**；令牌与 Register 见 [gRPC（Agent）](../reference/grpc-services.md) 与 [配置参考](../admin/configuration.md)。
