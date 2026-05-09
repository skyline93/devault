---
sidebar_position: 8
title: Web 控制台
description: 入口、认证与能力范围
---

# Web 控制台

## 入口

在控制面根地址下访问 **`/ui/jobs`**。**Agent 列表**（平台级、不按租户）：**`/ui/agents`**。**恢复演练 Cron**：**`/ui/restore-drill-schedules`**（见 [恢复演练](./restore-drill.md)）。

## 认证

使用 **HTTP Basic** 认证，密码为 **`DEVAULT_API_TOKEN`**（或与 REST 相同的 API 密钥 / OIDC Bearer 解析链一致的具体实现以服务端为准）。

## 能力范围

当前控制台侧重 **标准操作面**：

- Agent 登记列表（版本 / proto 合规；只读）
- 策略与调度的 **CRUD**
- 任务列表与状态、**立即备份**、Artifacts **恢复**、恢复演练调度 CRUD、任务**取消**/**重试**

复杂自动化、批量变更与多租户切换请优先使用 **HTTP API**、**CLI** 或贵司的上层平台。产品路线会持续增强控制台与 **SaaS 运营面**（租户切换、合规字段可视化等）的一致性。

## 与租户作用域的关系

浏览器请求**默认不携带** `X-DeVault-Tenant-Id`，与未带头部的 REST 调用一样使用 **`DEVAULT_DEFAULT_TENANT_SLUG`**（默认 **`default`**）解析租户。多租户日常操作请使用 API 显式带头或待控制台后续支持租户选择器。详见 [租户与访问控制](../admin/tenants-and-rbac.md)。
