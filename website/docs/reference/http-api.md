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
| `/api/v1/restore-drill-schedules` | 自动恢复演练 Cron（按 artifact 周期性 enqueue **`restore_drill`** Job） |
| `/api/v1/jobs` | 备份/恢复/恢复演练任务创建与查询（含 **`POST /jobs/restore-drill`**）；列表默认按 **`created_at` 倒序** |
| `/api/v1/artifacts` | 可恢复产物列表（含 **`retain_until`**、**`legal_hold`**）；**`PATCH …/artifacts/{id}/legal-hold`**（**admin**：设置法务保留） |
| `/api/v1/tenants` | **`GET`** 列表、**`POST`** 创建、**`PATCH /{tenant_id}`**（**admin**：BYOB/S3/KMS/强制加密等） |
| `/api/v1/agents` | 边缘 Agent 舰队清单（版本登记；不按租户切片） |

上述除 **`/tenants`**、**`/agents`** 外的资源均按 [租户与 HTTP 作用域](./tenants.md) 限定在某一租户内。

鉴权见 [API 访问控制](../security/api-access.md)。
