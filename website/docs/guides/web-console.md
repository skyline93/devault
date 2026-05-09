---
sidebar_position: 4
title: 简易 Web UI
description: Jobs UI 能力范围与认证方式
---

# 简易 Web UI

## 入口

在控制面根地址下访问 **`/ui/jobs`**（本地默认 `http://127.0.0.1:8000/ui/jobs`）。**Agent 舰队**（平台级、不按租户）见 **`/ui/agents`**。

## 认证

使用 **HTTP Basic** 认证，密码为环境变量 **`DEVAULT_API_TOKEN`**（与 API Bearer 令牌一致）。

## 能力范围

当前 UI 侧重开发/演示：

- **Agent** 登记列表（版本 / proto 合规；只读）
- 策略与调度的 **CRUD**
- 任务列表与状态查看
- **立即备份**、**恢复**、任务**取消**/**重试**

复杂运维场景请优先使用 API、CLI 或上层平台集成。

## 与租户作用域的关系

浏览器表单请求**不会**自动携带 `X-DeVault-Tenant-Id`，因此 UI 与未带头部的 REST 调用一样，使用 **`DEVAULT_DEFAULT_TENANT_SLUG`**（默认 **`default`**）解析租户。多租户运维请用 API 带头或扩展 UI。详见 [租户模型](../reference/tenants.md)。
