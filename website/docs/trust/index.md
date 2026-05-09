---
sidebar_position: 1
title: 信任中心导读
description: 安全与合规文档路径
---

# 信任中心导读

## 适用范围

面向 **安全评审、采购问卷与架构师**：信任边界、传输加密、静态加密、访问路径与审计。

落地部署、证书与告警实施见 [平台运维](../admin/index.md)（Compose/Helm、Envoy、[可观测性](../admin/observability.md)）。身份与租户模型见 [租户与访问控制](../admin/tenants-and-rbac.md)。

---

## 按任务选读

| 任务 | 建议顺序 |
|------|----------|
| **快速能力与边界对照** | [安全白皮书摘要](./whitepaper.md) |
| **Agent 出网、gRPC、防火墙** | [Agent 连接](./agent-connectivity.md) → [TLS 与网关](./tls-and-gateway.md) |
| **HTTP Bearer、Basic、RBAC** | [HTTP API 访问](./api-access.md) → [租户与访问控制](../admin/tenants-and-rbac.md) |
| **Artifact 加密与 KMS** | [Artifact 静态加密](./artifact-encryption.md) |

---

## 与其它章节的关系

- **「信任中心」**：说明安全模型与必选/可选控制。  
- **「运维」**：写清如何在你方环境中接通 TLS、轮转密钥、抓取审计与指标。  
- **「参考」**：OpenAPI、`proto` 与端口表，不重复安全论述。
