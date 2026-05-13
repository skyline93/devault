---
sidebar_position: 1
title: HTTP API
description: OpenAPI 入口与主要资源
---

# HTTP API

## Swagger / OpenAPI

启动控制面后浏览器打开 **`http://<host>:8000/docs`** 调试 **`/api/v1/*`**。

## 主要前缀

| 前缀 | 说明 |
|------|------|
| `/api/v1/policies` | 策略 CRUD |
| `/api/v1/schedules` | Cron 调度 CRUD |
| `/api/v1/restore-drill-schedules` | 恢复演练 Cron |
| `/api/v1/jobs` | 备份/恢复/演练；**`POST /jobs/restore-drill`** |
| `/api/v1/artifacts` | 列表、`retain_until`、`legal_hold`；**`PATCH …/legal-hold`** |
| `/api/v1/tenants` | 列表、创建、`PATCH`（admin：合规等） |
| `/api/v1/storage-profiles` | 平台存储 profile（**admin**，与控制台「对象存储」一致） |
| `/api/v1/agents` | Agent 舰队（不按租户切片） |

除 **`/tenants`**、**`/agents`** 外均按 [租户与访问控制](../admin/tenants-and-rbac.md) 限定租户。

鉴权见 [HTTP API 访问](../trust/api-access.md)。
