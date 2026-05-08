---
sidebar_position: 3
title: 简易 Web UI
description: Jobs UI 能力范围与认证方式
---

# 简易 Web UI

## 入口

在控制面根地址下访问 **`/ui/jobs`**（本地默认 `http://127.0.0.1:8000/ui/jobs`）。

## 认证

使用 **HTTP Basic** 认证，密码为环境变量 **`DEVAULT_API_TOKEN`**（与 API Bearer 令牌一致）。

## 能力范围

当前 UI 侧重开发/演示：

- 策略与调度的 **CRUD**
- 任务列表与状态查看
- **立即备份**、**恢复**、任务**取消**/**重试**

复杂运维场景请优先使用 API、CLI 或上层平台集成。
