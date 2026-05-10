---
sidebar_position: 2
title: 租户与访问控制
description: 数据模型、HTTP 作用域、RBAC、OIDC 与计费相关指标
---

# 租户与访问控制

## 数据模型

- **`tenants`**：`id`（UUID）、`name`、`slug`（唯一）、`created_at`。
- （迁移 **`0010`** 起）**合规与自带桶（BYOB）**可选字段：
  - **`require_encrypted_artifacts`** — 若为 **true**，该租户下**新策略/备份配置**不得关闭 **`encrypt_artifacts`**（与全局 **`DEVAULT_REQUIRE_ENCRYPTED_ARTIFACTS`** 叠加）。
  - **`kms_envelope_key_id`** — 默认 KMS CMK（KeyId/ARN）；在未写入策略 **`kms_envelope_key_id`** 时由 **`LeaseJobs` 下发的 `config_json`** 注入供 Agent 信封加密。
  - **`s3_bucket`** — 覆盖全局 **`DEVAULT_S3_BUCKET`**，该租户 artifact 的对象读写、预签名、Multipart 收尾与 scheduler 删除均使用该桶。
  - **`s3_assume_role_arn`** / **`s3_assume_role_external_id`** — STS **AssumeRole** 到客户账号；若设置则**优先于** **`DEVAULT_S3_ASSUME_ROLE_ARN`** 构造该租户的 S3 客户端。
- **`policies` / `jobs` / `schedules` / `artifacts`** 均带有 **`tenant_id`** 外键。
- **`artifacts.legal_hold`** — **true** 时保留清理不删除该行及对象。
- 迁移 **`0005`** 会创建 slug 为 **`default`** 的初始租户，并把现有行归属到该租户。

## HTTP API 与 Web UI

除 **`GET/POST /api/v1/tenants`** 与 **`PATCH /api/v1/tenants/{tenant_id}`**（**admin**：更新名称与 BYOB/合规字段）外，以下资源在读写时限定在当前租户：

- `/api/v1/policies`、`/schedules`、`/jobs`、`/artifacts`

**选择租户：**

1. 请求头 **`X-DeVault-Tenant-Id: <uuid>`**。
2. 省略时使用 **`DEVAULT_DEFAULT_TENANT_SLUG`**（默认 **`default`**）解析租户。

跨租户访问不存在的资源返回 **404**（不区分「不存在」与「无权访问」），避免 ID 枚举。

Web UI 与未带头部的 REST 使用相同默认 slug 解析。

### 创建额外租户

```http
POST /api/v1/tenants
Authorization: Bearer <token>
Content-Type: application/json

{"name": "Acme Corp", "slug": "acme"}
```

随后在业务请求上携带 **`X-DeVault-Tenant-Id`** 为新租户 `id`。

**幂等键**：`jobs.idempotency_key` 在 **同一 `tenant_id` 内** 唯一。

### Admin：更新租户（BYOB / 强制加密）

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

详见 [Artifact 静态加密](../trust/artifact-encryption.md)、[STS 与 AssumeRole](../storage/sts-assume-role.md)、[对象存储模型](../storage/object-store-model.md)。

## 对象存储键

文件备份 artifact 的稳定前缀形如：

`devault/<DEVAULT_ENV_NAME>/tenants/<tenant_id>/artifacts/<job_id>/`

对象名为 `bundle.tar.gz` 与 `manifest.json`。预颁发与 Agent 推导须与 **`LeaseJobs`** 下发的 **`tenant_id`** 一致。

---

## RBAC 与 HTTP 作用域

所有 **`/api/v1/policies`**、**`/schedules`**、**`/jobs`**、**`/artifacts`** 在解析租户后校验当前主体是否被允许访问该租户（**禁止通过换 UUID 枚举其他租户资源**）。

### 认证（按优先级）

对 **`Authorization: Bearer <token>`**（Web UI Basic **密码**与同一密钥链一致）：

1. **全局 OIDC JWT**（可选）：配置了 **`DEVAULT_OIDC_ISSUER`**、**`DEVAULT_OIDC_AUDIENCE`** 且 Bearer 为 JWT 时，按 OpenID Discovery 校验。角色来自 **`DEVAULT_OIDC_ROLE_CLAIM`**（默认 **`devault_role`**）：**`admin` \| `operator` \| `auditor`**。非 admin 时租户来自 **`DEVAULT_OIDC_TENANT_IDS_CLAIM`**（默认 **`devault_tenant_ids`**）。
2. **租户级 OIDC JWT（§十六-12）**：当 JWT 的 **`iss` / `aud`** 与某行 **`tenants.sso_oidc_issuer` / `sso_oidc_audience`**（成对配置、**租户间唯一**）一致时，在该租户 issuer 上再次 Discovery 并校验签名；解析为 **仅该租户** 作用域的 Bearer 主体（**`allowed_tenant_ids = {该租户}`**）。角色仍映射为 REST 的 **`admin` / `operator` / `auditor`**（与 **`tenant_memberships.role`** 语义对齐）。若 **`sso_jit_provisioning=true`** 且 JWT 含 **`sso_oidc_email_claim`**（默认 **`email`**），可在验证成功后 **JIT** 创建 **`console_users`**（随机密码哈希）并 **upsert `tenant_memberships`**。**`sso_password_login_disabled`**：若某用户**所有**成员关系所在租户均启用该开关，则 **`POST /api/v1/auth/login`**（邮箱密码）返回 **403**，须改用 **IdP JWT Bearer** 或调整成员关系。**SAML**：**`sso_saml_entity_id` / `sso_saml_acs_url`** 仅作运维登记，控制面 **不解析 SAML 断言**；典型做法是由 **IdP 网关 / 边缘代理** 换发 OIDC 或终止 SAML。
3. **数据库 API 密钥**：表 **`control_plane_api_keys`** 中 **`token_hash = SHA256(明文)`** 的启用行（**`devault-admin create-api-key`**）。
4. **遗留单令牌**：与 **`DEVAULT_API_TOKEN`** 完全相等时视为 **admin、全租户**。

若未配置 `DEVAULT_API_TOKEN`、未配置 OIDC、且无 API 密钥行，则控制面处于 **开发开放模式**（不校验 Bearer）。**生产与 SaaS 环境必须关闭该模式。**

### 租户成员邀请（§十六-11）

- **`POST /api/v1/tenants/{tenant_id}/invitations`**：平台 **admin** 或该租户 **`tenant_admin`**（Cookie 人机）可发邮件邀请；同一租户同一邮箱的未接受邀请在新建前会被撤销。
- **`GET /api/v1/tenants/{tenant_id}/invitations`**：列出待处理邀请。
- **`POST /api/v1/auth/invitations/accept`**：使用邮件中的 **token** 接受邀请；可创建 **`console_users`** 并写入 **`tenant_memberships`**，随后签发 **Cookie 会话**（与登录一致，含 **MFA** 策略）。环境变量见 **`DEVAULT_INVITATION_LINK_BASE`**、**`DEVAULT_INVITATION_TTL_HOURS`**（[配置参考](./configuration.md)）。

### 角色权限矩阵

| 能力 | admin | operator | auditor |
|------|:-----:|:--------:|:-------:|
| 读策略/调度/任务/artifact（租户内） | ✓ | ✓ | ✓ |
| 写策略/调度、触发备份/恢复、取消/重试 | ✓ | ✓ | ✗ |
| **`POST /api/v1/tenants`** | ✓ | ✗ | ✗ |
| **`PATCH /api/v1/tenants/{id}`**（BYOB、强制加密等） | ✓ | ✗ | ✗ |
| **`GET /api/v1/tenants`** | 全部 | 允许的 `tenant_id` | 允许的 `tenant_id` |
| **`PATCH /api/v1/artifacts/{id}/legal-hold`** | ✓（admin，且 header 租户匹配） | ✗ | ✗ |
| **Agent gRPC** | ✓ | ✓ | ✗（`PERMISSION_DENIED`） |

### 创建数据库 API 密钥

```bash
devault-admin create-api-key --name ci-operator --role operator --tenant <uuid>
```

打印 **一次性明文令牌**；用作 **`Authorization: Bearer …`** 或 UI 密码。

- **`--role admin`**：可不传 `--tenant`（全租户）。
- **`operator` / `auditor`**：至少一个 **`--tenant`**。

### 用量与请求指标（计费 / 配额）

- **`devault_http_requests_total`**：`method`、`path_template`。
- **`devault_billing_committed_backup_bytes_total`**：`tenant_id` — 备份 **`CompleteJob`** 成功按 **`size_bytes`** 递增，便于按租户汇总体量。

### 运维提示

- 生产应使用强随机 **`DEVAULT_API_TOKEN`** 或 **仅数据库密钥 + OIDC**，并关闭开发开放模式。
- OIDC 与静态密钥可并存：JWT 先解析，失败再回落哈希表与单令牌。

## 相关文档

- [HTTP API](../reference/http-api.md)  
- [API 访问（HTTP/Basic）](../trust/api-access.md)  
- [gRPC（Agent）](../reference/grpc-services.md)
