---
sidebar_position: 1
title: DeVault 是什么
description: 产品定位、适用场景与术语表
---

# DeVault 是什么

DeVault 是面向开发者与小团队的**自托管备份与恢复平台**：控制面提供 HTTP API、gRPC 与简易 Web UI；边缘 **Agent** 通过 gRPC 拉取任务，使用 **S3 兼容对象存储**完成数据面直传。

## 适用场景

- 本地或 Compose 环境中的**文件全量备份与恢复**
- 需要 **Cron 定时**、任务取消/重试、同策略并发控制的备份作业
- 希望与 **MinIO / 云厂商 S3** 集成、并暴露 **Prometheus 指标** 的部署

## 与常见方案的关系

DeVault 强调**控制面与 Agent 分离**、**Pull 模型**与**预签名直传**，便于在网关后扩展 gRPC，并将对象存储权限收敛到最小。它并非「企业级全家桶备份套件」，而是以可运行、可扩展的 MVP 为核心。

## 术语表

| 术语 | 含义 |
|------|------|
| **控制面** | 提供 HTTP API、gRPC（与 API 同进程时可由 `DEVAULT_GRPC_LISTEN` 开启）、策略/调度/任务状态、预签名签发等逻辑的服务 |
| **Agent** | 边缘进程，仅连接 gRPC 与 S3（及本地允许路径），执行实际备份/恢复 |
| **任务（Job）** | 一次备份或恢复的执行单元，有状态机与重试语义 |
| **策略（Policy）** | 描述备份什么、如何备份（如文件路径、插件配置） |
| **调度（Schedule）** | Cron 表达式与策略绑定，由调度器创建待处理任务 |
| **租约** | Agent 通过 gRPC 拉取的工作租约，用于领取待执行任务 |
| **Artifact** | 备份完成后在元数据中登记的可恢复产物引用 |

下一步建议阅读 [快速开始](./quickstart.md)、[架构概览](./architecture-overview.md) 与 [目标架构](./target-architecture.md)（控制/数据面与 Pull 序列）。
