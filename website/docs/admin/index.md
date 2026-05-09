---
sidebar_position: 1
title: 平台运维导读
description: 运维文档阅读路径与适用范围
---

# 平台运维导读

## 适用范围

| 读者 | 建议 |
|------|------|
| **租户内操作员**（只调 API / Web 控制台） | 优先 [使用手册](../user/index.md)、[HTTP API](../reference/http-api.md) |
| **平台 / SRE**（自建或专属部署控制面） | 使用本章节 |
| **安全架构**（评审信任域） | 同步阅读 [信任中心](../trust/index.md) |

术语与租户、RBAC、HTTP 头约定以 **[租户与访问控制](./tenants-and-rbac.md)** 为准；全站统称为 **Web 控制台**（路径前缀 `/ui`）。

---

## 按任务选读（三条路径）

### 路径 A：本地或演示栈跑通

1. [环境与依赖](./requirements.md) → [Docker Compose](./docker-compose.md)  
2. [配置参考](./configuration.md)、[数据库迁移](./database-migrations.md)  
3. [对象存储模型](../storage/object-store-model.md)、[租户与访问控制](./tenants-and-rbac.md)（多租户上线前必读）

验证：`GET /healthz`、Swagger `/docs`、控制台 `/ui/jobs`。

### 路径 B：Kubernetes 与生产编排

1. [Kubernetes（Helm）](./kubernetes-helm.md)  
2. [配置参考](./configuration.md)、[数据库迁移](./database-migrations.md)（**迁移仅由一个 Job 或单副本 api 执行**）  
3. [可观测性](./observability.md)、[TLS 与网关](../trust/tls-and-gateway.md)（gRPC 对外）  
4. [gRPC 与 API 多实例](./grpc-multi-instance.md)、[企业参考架构](./enterprise-reference-architecture.md)

### 路径 C：灾备与高阶运维

1. [控制面元数据库备份与 DR](./control-plane-database-dr.md)（与业务 Artifact 备份不同）  
2. [可观测性](./observability.md) 告警与指标  
3. [存储调优](../storage/tuning.md)、[大对象](../storage/large-objects.md)、[STS](../storage/sts-assume-role.md)

**Agent 版本与会话**：运维入口 [Agent 舰队](./agent-fleet.md)。
