---
sidebar_position: 5
title: 安全白皮书摘要
description: 信任边界、密钥流、审计面与合规路线（含明确不支持的项）
---

# 安全白皮书摘要

本文面向**安全评审与采购问卷**的速览，不是法律意义上的「白皮书」全文；技术行为以代码与 [TLS 与网关](./tls-and-gateway.md)、[API 访问](./api-access.md)、[Artifact 静态加密](./artifact-encryption.md) 为准。

## 信任边界

| 域 | 持有或处理的内容 | 不持有 |
|----|-------------------|--------|
| **客户内网（Agent）** | 数据源文件、可选 **`DEVAULT_ARTIFACT_ENCRYPTION_KEY`**、Register 换得的 **Bearer** | 平台 Postgres/Redis 连接串、桶长期根密钥（默认形态） |
| **公网/专线可达区（网关）** | TLS 会话、（可选）mTLS 客户端身份 | 业务备份明文（payload 为 gRPC 元数据与作业描述，非对象体） |
| **控制面 VPC** | 作业与 Artifact 元数据、预签名策略、审计日志 | 客户源文件内容（不经控制面磁盘持久化为备份体） |
| **对象存储** | **bundle / manifest** 对象、服务端加密（若桶启用） | Agent 进程内存外的「备份中」流式数据由 Agent 直写 |

## 密钥与凭证流（摘要）

1. **REST / UI**：静态 **`DEVAULT_API_TOKEN`**、数据库 **`control_plane_api_keys`**（哈希存证）、或 **OIDC JWT**（[访问控制](../reference/access-control.md)）。
2. **Agent gRPC**：开发态可用共享 Token；生产建议 **TLS**、**`DEVAULT_GRPC_REGISTRATION_SECRET`** 引导 **Register**，并结合网关 **mTLS**（见 [Agent 连通性](./agent-connectivity.md)）。
3. **数据面**：控制面为每个 Job 签发 **时效受限** 的 **预签名** GET/PUT（及 Multipart 控制流）；控制面访问云厂商 API 可使用 **STS AssumeRole** 短时会话（[STS 与 AssumeRole](../storage/sts-assume-role.md)）。
4. **Artifact 加密（可选）**：AES-256-GCM 在 **Agent** 侧对 bundle 加密后再上传；密钥由运维注入 **`DEVAULT_ARTIFACT_ENCRYPTION_KEY`**，控制面不保存该对称密钥材料。

## 审计面

- **HTTP**：访问日志由反向代理或运行时采集。
- **gRPC**：启用 **`DEVAULT_GRPC_AUDIT_LOG`** 时，logger **`devault.grpc.audit`** 输出每 RPC 一行 JSON（**不含**密钥与预签名完整 URL）；字段含 `rpc`、`peer`、`grpc_code`、`elapsed_ms` 等。

## 备份验证与持续信任（运维视角）

- **恢复演练（restore drill）**：周期性从 Artifact 拉取、校验、解压至隔离目录；见 [恢复演练指南](../guides/restore-drill.md)。
- **指标与告警**：**`devault_jobs_total`**（含 **`error_class`**）、**`devault_backup_integrity_control_rejects_total`**、**`devault_jobs_overdue_nonterminal`**；示例规则见 [可观测性](../install/observability.md#backup-integrity-and-sla-alerts)。

## 合规与路线图（诚实表述）

| 能力 | 状态 |
|------|------|
| 传输中加密（gRPC TLS、HTTPS 预签名） | 已支持（配置驱动） |
| 静态 Artifact 加密（Agent 侧） | 已支持（可选策略） |
| 租户隔离、RBAC、可选 OIDC | 已支持 |
| 保留期与对象删除 | 已支持（scheduler + 存储 API） |
| **KMS / 信封 / 按租户 DEK** | **规划中**（见企业待办 §五） |
| **WORM / Object Lock、Legal Hold** | **未实现** |
| **BYOB（客户自带桶）** | **未实现** |
| **增量 DB、PITR** | **非当前文件备份主线**（M2 数据库 Epic） |

## 相关文档

- [目标架构（边缘 Agent + 控制面）](../intro/target-architecture.md)
- [企业部署参考架构](../install/enterprise-reference-architecture.md)
- [访问控制与 RBAC](../reference/access-control.md)
- [租户](../reference/tenants.md)
