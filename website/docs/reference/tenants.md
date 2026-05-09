---
sidebar_position: 4
title: 租户模型与 HTTP 作用域
description: tenants 表、默认租户与 X-DeVault-Tenant-Id
---

# 租户模型与 HTTP 作用域

## 数据模型

- **`tenants`**：`id`（UUID）、`name`、`slug`（唯一）、`created_at`。
- （迁移 **`0010`** 起）**合规与自带桶（BYOB）**可选字段：
  - **`require_encrypted_artifacts`** — 若为 **true**，该租户下**新策略/备份配置**不得关闭 **`encrypt_artifacts`**（与全局 **`DEVAULT_REQUIRE_ENCRYPTED_ARTIFACTS`** 叠加）。
  - **`kms_envelope_key_id`** — 默认 KMS CMK（KeyId/ARN）；在未写入策略 **`kms_envelope_key_id`** 时，由 **`LeaseJobs` 下发的 `config_json`** 注入供 Agent 信封加密。
  - **`s3_bucket`** — 覆盖全局 **`DEVAULT_S3_BUCKET`**，该租户 artifact 的对象读写、预签名、Multipart 收尾与 scheduler 删除均使用该桶。
  - **`s3_assume_role_arn`** / **`s3_assume_role_external_id`** — 为该租户 STS **AssumeRole** 到客户账号（可选 **ExternalId**）；若设置则**优先于** **`DEVAULT_S3_ASSUME_ROLE_ARN`** 用于构造该租户的 S3 客户端。
- **`policies` / `jobs` / `schedules` / `artifacts`** 均带有 **`tenant_id`** 外键，保证元数据按租户隔离。
- **`artifacts.legal_hold`** — 若为 **true**，保留清理不会删除该行及对象（Legal Hold）。
- 迁移 **`0005`** 会创建 slug 为 **`default`** 的初始租户，并把现有行全部归属到该租户。

## HTTP API 与 Web UI

除 **`GET/POST /api/v1/tenants`** 与 **`PATCH /api/v1/tenants/{tenant_id}`**（**admin**：更新名称与上述 BYOB/合规字段；受 API Key 租户范围约束）外，以下资源在读写时都会限定在当前租户：

- `/api/v1/policies`、`/schedules`、`/jobs`、`/artifacts`

**选择租户的方式：**

1. 请求头 **`X-DeVault-Tenant-Id: <uuid>`** — 显式指定租户。
2. 若省略该头，则使用环境变量 **`DEVAULT_DEFAULT_TENANT_SLUG`**（默认 **`default`**）在数据库中解析对应租户。

跨租户访问不存在的资源时返回 **404**（不区分「不存在」与「属于其他租户」），避免 ID 枚举。

简易 Web UI（`/ui/*`）与 REST 使用相同解析规则；未登录浏览器无法自定义头时，将使用默认 slug 对应租户（单租户演示场景）。

## 对象存储键

S3（及本地存储逻辑路径）中，文件备份 artifact 的稳定前缀为：

`devault/<DEVAULT_ENV_NAME>/tenants/<tenant_id>/artifacts/<job_id>/`

具体对象名为 `bundle.tar.gz` 与 `manifest.json`。控制面在 **`RequestStorageGrant`** 与 Agent 本地推导必须与 **`LeaseJobs`** 下发的 **`config_json` 内 `tenant_id`** 一致。

## Admin：更新租户（BYOB / 强制加密）

```http
PATCH /api/v1/tenants/<tenant_uuid>
Authorization: Bearer <admin token>
Content-Type: application/json

{
  "s3_bucket": "customer-owned-bucket",
  "s3_assume_role_arn": "arn:aws:iam::123456789012:role/devault-tenant-acme",
  "s3_assume_role_external_id": "optional-external-id",
  "kms_envelope_key_id": "arn:aws:kms:...:key/...",
  "require_encrypted_artifacts": true,
  "name": "Acme Corp"
}
```

空字符串可清除可选字符串字段（实现为 strip 后置 **null**）。详见 [Artifact 静态加密](../security/artifact-encryption.md) 与 [STS 与 AssumeRole](../storage/sts-assume-role.md)。

## 创建额外租户

```http
POST /api/v1/tenants
Authorization: Bearer <token>
Content-Type: application/json

{"name": "Acme Corp", "slug": "acme"}
```

随后在业务请求上携带 **`X-DeVault-Tenant-Id`** 为新租户 `id` 即可在该租户下创建策略与任务。

**幂等键**：`jobs.idempotency_key` 在 **同一 `tenant_id` 内** 唯一（跨租户可重复相同字符串）。

## 访问控制（RBAC / OIDC）

角色、数据库 API 密钥、可选 OIDC JWT 与 Agent gRPC 限制见 **[访问控制与 RBAC](./access-control.md)**。
