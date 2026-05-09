---
sidebar_position: 6
title: 访问控制与 RBAC
description: API 密钥、角色、OIDC 可选与用量指标
---

# 访问控制与 RBAC

## 与租户作用域的关系

所有 **`/api/v1/policies`**、**`/schedules`**、**`/jobs`**、**`/artifacts`** 请求在解析 **`X-DeVault-Tenant-Id`**（或默认 slug）后，还会校验当前主体是否被允许访问该租户（**不允许通过换 UUID 枚举其他租户资源**）。详见 [租户模型](./tenants.md)。

## 认证方式（按优先级）

对 **`Authorization: Bearer <token>`**（以及 Web UI 的 Basic **密码**字段，作为同一秘密）：

1. **OIDC JWT**（可选）：若配置了 **`DEVAULT_OIDC_ISSUER`** 与 **`DEVAULT_OIDC_AUDIENCE`**，且 Bearer 串为三段式 JWT，则按发行方 **OpenID Discovery** 拉取 JWKS 校验签名、`iss`、`aud`、`exp`。角色来自声明 **`DEVAULT_OIDC_ROLE_CLAIM`**（默认 **`devault_role`**），取值 **`admin` \| `operator` \| `auditor`**。非 admin 时，租户范围来自 **`DEVAULT_OIDC_TENANT_IDS_CLAIM`**（默认 **`devault_tenant_ids`**，JSON 数组或逗号分隔 UUID 字符串）。
2. **数据库 API 密钥**：表 **`control_plane_api_keys`** 中 **`token_hash = SHA256(明文)`** 的启用行（由 **`devault-admin create-api-key`** 创建）。
3. **遗留单令牌**：与 **`DEVAULT_API_TOKEN`** 完全相等（`secrets.compare_digest`）时视为 **admin、全租户**。

若 **未** 配置 `DEVAULT_API_TOKEN`、**未** 配置 OIDC、且 **不存在** 任何 API 密钥行，则控制面保持与早期版本一致的 **开发开放模式**（不校验 Bearer）。

## 角色与权限矩阵

| 能力 | admin | operator | auditor |
|------|:-----:|:--------:|:-------:|
| 读策略/调度/任务/artifact（在租户范围内） | ✓ | ✓ | ✓ |
| 写策略/调度、触发备份/恢复、取消/重试 | ✓ | ✓ | ✗ |
| **`POST /api/v1/tenants`**（创建租户） | ✓ | ✗ | ✗ |
| **`PATCH /api/v1/tenants/{id}`**（BYOB、强制加密、默认 CMK 等） | ✓（**admin**） | ✗ | ✗ |
| **`GET /api/v1/tenants`** | 全部 | 仅允许的 `tenant_id` | 仅允许的 `tenant_id` |
| **`PATCH /api/v1/artifacts/{id}/legal-hold`**（**`legal_hold`** 布尔） | ✓（**admin**，且 **header 租户**包含该 artifact） | ✗ | ✗ |
| **Agent gRPC**（租约、存储授权等） | ✓ | ✓ | ✗（`PERMISSION_DENIED`） |

## 创建数据库 API 密钥

在能访问元数据库的环境执行（需 **`DEVAULT_DATABASE_URL`**）：

```bash
devault-admin create-api-key --name ci-operator --role operator --tenant <uuid>
```

命令会打印 **一次性明文令牌**；将其作为 **`Authorization: Bearer …`** 或 UI Basic 密码使用。

- **`--role admin`**：可不传 `--tenant`，表示全租户。
- **`operator` / `auditor`**：必须至少一个 **`--tenant`**（可重复或逗号分隔）。

## 用量与请求指标（计费埋点）

- **`devault_http_requests_total`**：`method`、`path_template`（HTTP 中间件）。
- **`devault_billing_committed_backup_bytes_total`**：`tenant_id` — 在 Agent **`CompleteJob`** 成功写入 artifact 时按声明的 **`size_bytes`** 递增，便于按租户汇总备份体量（计费/配额信号）。

## 运维提示

- 生产环境应 **同时** 使用强随机 **`DEVAULT_API_TOKEN`** 或仅使用 **数据库密钥 + OIDC**，并关闭开发开放模式。
- OIDC 与静态密钥可同时启用：JWT 会先尝试 OIDC 解析，失败则回落到哈希表与单令牌（便于迁移）。
