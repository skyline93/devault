---
sidebar_position: 3
title: API 访问控制
description: HTTP Bearer 与简易 Web UI 认证
---

# API 访问控制

## HTTP API

REST 调用在 `Authorization` 头携带 **Bearer** 令牌：

```http
Authorization: Bearer <DEVAULT_API_TOKEN>
```

`DEVAULT_API_TOKEN` 在控制面环境中配置；Compose 演示默认常为 `changeme`。

## 多租户 HTTP 作用域

对 **`/api/v1/policies`**、**`/schedules`**、**`/jobs`**、**`/artifacts`** 的读写，可带请求头：

```http
X-DeVault-Tenant-Id: <tenant-uuid>
```

省略时由 **`DEVAULT_DEFAULT_TENANT_SLUG`**（默认 `default`）解析租户。详见 [租户模型](../reference/tenants.md)。

## RBAC 与数据库 API 密钥

除 **`DEVAULT_API_TOKEN`** 外，可写入表 **`control_plane_api_keys`**（迁移 **`0006`**）使用 **SHA256(明文)** 存储的 Bearer 密钥，并绑定 **`admin` / `operator` / `auditor`** 与可选租户 UUID 列表。创建命令：**`devault-admin create-api-key`**。权限矩阵与可选 **OIDC JWT** 见 [访问控制与 RBAC](../reference/access-control.md)。

## 简易 Web UI

浏览器访问 **`/ui/jobs`** 等路径时使用 **HTTP Basic** 认证：

- 用户名可随意（实现若不要求固定用户名）
- 密码为 **`DEVAULT_API_TOKEN`** 或与 REST 相同的 **数据库 API 密钥明文** / **OIDC 场景下的 JWT**（与 Bearer 解析链一致）

生产环境请使用强随机令牌，并配合 HTTPS 与网络策略。

## 与 OpenAPI 的关系

交互式 API 文档见 **`/docs`**（Swagger UI）。更多路径见 [HTTP API 参考](../reference/http-api.md)。
