---
sidebar_position: 5
title: HTTP API 访问
description: Bearer、多租户请求头与 Web UI Basic
---

# HTTP API 访问

## Bearer

```http
Authorization: Bearer <DEVAULT_API_TOKEN>
```

`DEVAULT_API_TOKEN` 在控制面环境中配置；Compose 演示默认常为 `changeme`。**生产与 SaaS 必须使用强随机或 OIDC/数据库密钥链。**

## 多租户 HTTP 作用域

```http
X-DeVault-Tenant-Id: <tenant-uuid>
```

省略时使用 **`DEVAULT_DEFAULT_TENANT_SLUG`**（默认 `default`）。详见 [租户与访问控制](../admin/tenants-and-rbac.md)。

## RBAC 与数据库 API 密钥

表 **`control_plane_api_keys`**、`devault-admin create-api-key`、OIDC JWT 与权限矩阵见 **[租户与访问控制](../admin/tenants-and-rbac.md)**。

## Web UI

**`/ui/*`** 使用 **HTTP Basic**：密码为 **`DEVAULT_API_TOKEN`** 或与 REST 相同的密钥链可解析值。生产须 **HTTPS**。

## OpenAPI

交互式文档：**`/docs`**（见 [HTTP API](../reference/http-api.md)）。
