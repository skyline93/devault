---
sidebar_position: 2
title: 策略与定时
description: 策略、Cron 调度与并发语义
---

# 策略与定时

## 策略（Policy）

策略描述**备份什么**与**如何备份**（插件、`config` 等）。HTTP 资源路径为 **`/api/v1/policies`**（详见 OpenAPI）。策略归属某一**租户**（`tenant_id`）；API 通过 **`X-DeVault-Tenant-Id`** 或默认 slug 限定作用域，见 [租户模型](../reference/tenants.md)。

## 调度（Schedule）

调度将 **Cron 表达式** 与策略绑定，由 **scheduler** 服务周期性地**创建待处理任务**。API 路径为 **`/api/v1/schedules`**。

## 并发与锁

同一策略上可能存在**同策略并发锁**，避免重复全量备份彼此踩踏；具体字段名与行为以 OpenAPI 与实现为准。

## 立即执行

简易 UI 与 API 支持在已有策略上触发「立即备份」类操作；任务仍走统一队列与 Agent 拉取模型。
