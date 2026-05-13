---
sidebar_position: 2
title: 安全白皮书摘要
description: 信任边界、密钥流、审计面与合规能力对照
---

# 安全白皮书摘要

本文面向 **安全评审与问卷**速览；具体行为以当前代码及 [TLS 与网关](./tls-and-gateway.md)、[HTTP API 访问](./api-access.md)、[Artifact 静态加密](./artifact-encryption.md) 为准。

## 信任边界

| 域 | 持有或处理的内容 | 不持有 |
|----|-------------------|--------|
| **客户内网（Agent）** | 数据源文件、可选 **`DEVAULT_ARTIFACT_ENCRYPTION_KEY`**、Register Bearer | 平台 Postgres/Redis 连接串、桶长期根密钥（默认形态） |
| **公网/专线可达区（网关）** | TLS、mTLS（可选）、会话审计 | 备份明文 payload（gRPC 为作业描述与元数据，非对象体） |
| **控制面 VPC** | 作业与 Artifact 元数据、预签名策略、审计日志 | 客户源文件内容不经控制面持久化为备份体 |
| **对象存储** | bundle / manifest、桶 SSE（若启用） | 「备份中」字节流由 Agent 直写 |

## 密钥与凭证流（摘要）

1. **REST / Web 控制台**： **`DEVAULT_API_TOKEN`**、**`control_plane_api_keys`**（哈希）、或 **OIDC JWT**（见 [租户与访问控制](../admin/tenants-and-rbac.md)）。
2. **Agent gRPC**： **`DEVAULT_GRPC_REGISTRATION_SECRET`** 引导 **Register**，生产配合 **TLS / mTLS**（见 [Agent 连接](./agent-connectivity.md)）。
3. **数据面**：按 Job 签发的 **短时预签名**；控制面可用 **STS AssumeRole**（见 [STS](../storage/sts-assume-role.md)）。
4. **Artifact 加密（可选）**：AES-256-GCM 在 **Agent** 侧加密后再上传（见 [Artifact 静态加密](./artifact-encryption.md)）。

## 审计面

- **HTTP**：反向代理或运行时访问日志。
- **gRPC**：**`DEVAULT_GRPC_AUDIT_LOG`** → logger **`devault.grpc.audit`** 每 RPC 一行 JSON（不含完整预签名 URL）。

## 备份验证

- **恢复演练**：见 [恢复演练](../user/restore-drill.md)。
- **指标与告警**：见 [可观测性](../admin/observability.md#backup-integrity-and-sla-alerts)。

## 能力与边界（与当前主线对照）

| 能力 | 状态 |
|------|------|
| 传输中加密（gRPC TLS、HTTPS 预签名） | **已支持**（配置驱动） |
| 静态 / KMS 信封 Artifact 加密（Agent 侧） | **已支持**（策略与租户级 CMK 配置） |
| 租户隔离、RBAC、可选 OIDC | **已支持** |
| 保留期与元数据驱动对象删除 | **已支持** |
| **Legal hold**（元数据 + 清理跳过） | **已支持**（API；与 S3 Bucket Legal Hold 无自动绑定） |
| **多 profile / AssumeRole** | **已支持**（`storage_profiles` + STS；静态密钥 Fernet 加密） |
| **S3 Object Lock（WORM）** | **已支持**（策略 `object_lock_mode` / `object_lock_retain_days`；桶须开启 Object Lock） |
| **增量数据库备份插件** | **非当前文件备份主线**（后续插件方向） |

SaaS **商业包装层**（SOC2 报告模板、数据驻留承诺书等）由产品与法务在发行策略中单独交付；技术行为以本节与代码为准。

## 相关文档

- [平台实现架构](../engineering/platform-architecture.md)
- [企业参考架构](../admin/enterprise-reference-architecture.md)
- [租户与访问控制](../admin/tenants-and-rbac.md)
