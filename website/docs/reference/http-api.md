---
sidebar_position: 1
title: HTTP API
description: OpenAPI 入口与主要资源
---

# HTTP API

## Swagger / OpenAPI

启动控制面后，在浏览器打开：

**`http://<host>:8000/docs`**

可交互调试 **`/api/v1/*`** 下的策略、调度、任务、artifact 等资源。

## 主要前缀

| 前缀 | 说明 |
|------|------|
| `/api/v1/policies` | 策略 CRUD |
| `/api/v1/schedules` | Cron 调度 CRUD |
| `/api/v1/jobs` | 备份/恢复任务创建与查询 |
| `/api/v1/artifacts` | 可恢复产物列表 |

鉴权见 [API 访问控制](../security/api-access.md)。
