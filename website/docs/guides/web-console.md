---
sidebar_position: 4
title: 简易 Web UI
description: Jobs UI 能力范围与认证方式
---

# 简易 Web UI

## 入口

在控制面根地址下访问 **`/ui/jobs`**（本地默认 `http://127.0.0.1:8000/ui/jobs`）。**Agent 舰队**（平台级、不按租户）见 **`/ui/agents`**。**恢复演练 Cron** 见 **`/ui/restore-drill-schedules`**（与 [自动恢复演练](./restore-drill.md) 一致）。

## 认证

使用 **HTTP Basic** 认证，密码为环境变量 **`DEVAULT_API_TOKEN`**（与 API Bearer 令牌一致）。

## 能力范围

当前 UI 侧重开发/演示：

- **Agent** 登记列表（版本 / proto 合规；只读）
- 策略与调度的 **CRUD**
- 任务列表与状态查看
- **立即备份**、Artifacts **Restore**（每行按钮打开弹窗表单后提交）、**恢复演练调度** CRUD（**`/ui/restore-drill-schedules`**；一次性演练用 API）、任务**取消**/**重试**

复杂运维场景请优先使用 API、CLI 或上层平台集成。

## 企业级能力对齐（规划）

以下能力在 **REST** 与 **§五** 合规主线已支持，**简易 UI 尚未完全覆盖**；优先排期见仓库 **`docs-old/enterprise-backlog.md`** 全量索引 **八-04～八-09** 与 Epic **`E-UX-001`**（策略 **KMS / Object Lock**、租户 **BYOB·合规**、租户切换、**Artifacts** 列、**Legal Hold**、运维快捷入口等）。

## 与租户作用域的关系

浏览器表单请求**不会**自动携带 `X-DeVault-Tenant-Id`，因此 UI 与未带头部的 REST 调用一样，使用 **`DEVAULT_DEFAULT_TENANT_SLUG`**（默认 **`default`**）解析租户。多租户运维请用 API 带头或扩展 UI。详见 [租户模型](../reference/tenants.md)。
