---
sidebar_position: 5
title: HTTP API 访问
description: Bearer、Cookie 会话、多租户请求头
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

## Web 控制台（`console/`）

人机主路径：**Cookie 会话**（**`POST /api/v1/auth/login`**，**httpOnly** + **Redis**）；租户策略可要求 **TOTP**（**`POST /api/v1/auth/mfa/verify`**，**`AuthSessionOut.needs_mfa`**）；写请求带 **CSRF**（**`X-CSRF-Token`** 与 **`devault_csrf`** Cookie）。可选 **`Authorization: Bearer`**（与 REST 相同解析链：全局 **OIDC**、**租户级 OIDC**（**`iss`/`aud`** 匹配 **`tenants`** 行）、API 密钥、遗留令牌；控制台 **`/user/integration`**）。生产须 **HTTPS**，并设置 **`DEVAULT_SESSION_COOKIE_SECURE=true`** 等 Cookie 属性。

## OpenAPI

交互式文档：**`/docs`**（见 [HTTP API](../reference/http-api.md)）。
