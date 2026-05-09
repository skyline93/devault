---
sidebar_position: 2
title: 核心概念
description: 控制面、Agent、任务与多租户术语
---

# 核心概念

DeVault 将 **编排与元数据** 集中在控制面，将 **实际读写数据源与对象存储** 放在边缘 Agent。平台以 **多租户 SaaS** 为元数据模型：策略、作业与 Artifact 均归属于租户。

## 术语表

| 术语 | 含义 |
|------|------|
| **控制面** | 提供 HTTP API、gRPC（`DEVAULT_GRPC_LISTEN`）、策略/调度/任务状态、预签名签发等的服务 |
| **Agent** | 边缘进程：连接 gRPC 与 S3（及本地允许路径），执行备份/恢复 |
| **租户（Tenant）** | 元数据与默认存储作用域隔离单元；REST 通过 `X-DeVault-Tenant-Id` 或默认 slug 选定 |
| **任务（Job）** | 一次备份、恢复或恢复演练的执行单元，具备状态机与重试语义 |
| **策略（Policy）** | 描述备份什么、如何备份（插件、`config` 等） |
| **调度（Schedule）** | Cron 表达式与策略绑定，由调度器创建待处理任务 |
| **租约（Lease）** | Agent 通过 `LeaseJobs` 领取的作业租约 |
| **Artifact** | 备份成功后登记的可恢复产物引用（manifest / bundle） |

权限模型（admin / operator / auditor）与 API 密钥见 [租户与访问控制](../admin/tenants-and-rbac.md)。

## 延伸阅读

- [架构一页纸](../product/architecture.md)  
- [快速开始](./quickstart.md)
