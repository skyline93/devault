---
sidebar_position: 2
title: 部署形态
description: 云 SaaS、专属部署与自托管对照
---

# 部署形态

DeVault 控制面与 Agent 架构 **与交付形态解耦**。以下分类帮助读者在文档中找到正确操作路径。

## 云多租户 SaaS（目标形态）

- **控制面**：由服务商统一运维、升级与扩缩容；客户通过 **HTTPS / gRPC 终端**接入。
- **租户**：逻辑隔离在元数据与存储前缀；身份与权限见 [租户与访问控制](../admin/tenants-and-rbac.md)。
- **Agent**：部署在客户网络或受控环境，仅 **出站** 连接平台与对象存储端点。
- **文档侧重**：[使用手册](../user/index.md)、[信任中心](../trust/index.md)、[API 参考](../reference/http-api.md)。

## 专属单租（VPC / 专有云）

- **控制面**：单一客户专用实例或集群，网络与数据驻留按合同约束。
- **运维责任**：通常由客户或托管方承担升级、备份元数据库与观测；手册见 [平台运维](../admin/index.md) 全篇。
- **文档侧重**：与自托管相同的技术章节，另加合同中的 **SLA、支持与变更窗口**。

## 自托管（自带基础设施）

- 使用仓库提供的 **Docker Compose**、**Helm Chart** 或自建编排启动控制面、调度器、PostgreSQL、Redis 与对象存储。
- **文档侧重**：[平台运维](../admin/index.md) 中的安装、配置、多实例、DR 与可观测性。

## 阅读路径建议

| 你的目标 | 建议章节 |
|----------|----------|
| 理解信任边界与网络 | [架构一页纸](./architecture.md)、[信任中心](../trust/index.md)、[Agent 连接](../trust/agent-connectivity.md) |
| 跑通备份与恢复 | [快速开始](../user/quickstart.md)、[备份与恢复流程](../user/backup-and-restore.md) |
| 上线生产 | [平台运维](../admin/index.md)、[企业参考架构](../admin/enterprise-reference-architecture.md) |
| 对接自动化 | [HTTP API](../reference/http-api.md)、[gRPC（Agent）](../reference/grpc-services.md) |
