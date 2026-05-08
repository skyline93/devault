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

## 简易 Web UI

浏览器访问 **`/ui/jobs`** 等路径时使用 **HTTP Basic** 认证：

- 用户名可随意（实现若不要求固定用户名）
- 密码为 **`DEVAULT_API_TOKEN`**

生产环境请使用强随机令牌，并配合 HTTPS 与网络策略。

## 与 OpenAPI 的关系

交互式 API 文档见 **`/docs`**（Swagger UI）。更多路径见 [HTTP API 参考](../reference/http-api.md)。
