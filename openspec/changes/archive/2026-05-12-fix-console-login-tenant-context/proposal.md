# Change: 控制台登录与租户上下文解耦

## Why

人机通过外部 IAM（`POST …/v1/auth/login`）登录时，Console 的全局请求拦截器会把 `localStorage` 中的 `devault_tenant_id` 自动加到 **`X-DeVault-Tenant-Id`**。IAM 将请求头与 body 中的 `tenant_id` 一并解析为「本次登录请求的租户」。当存在**过期会话残留**（例如 401 仅清除 Bearer、未清除租户）、**换账号**或 **平台管理员**（禁止携带租户）时，会导致登录失败或表现为「登录依赖租户 ID」，与产品预期（登录阶段不依赖租户）不一致。

## What Changes

- **Console**：对 IAM 认证相关请求（至少 `…/v1/auth/login`、`…/v1/auth/refresh`）**不自动附加** `X-DeVault-Tenant-Id`（或等价：凡发往 `UMI_APP_IAM_PREFIX` 的请求不加租户头，与当前仅登录调用 IAM 的范围一致）。
- **Console**：在 **401** 触发跳转登录页的同一清理路径中，**同时移除** `devault_tenant_id` 本地缓存，避免脏租户污染下一次 IAM 登录。
- **文档**：在 `console/README.md`（或相关 trust/console 文档）中简短说明「IAM 登录/刷新请求不应携带租户头；租户上下文在登录成功后由会话与顶栏选择器维护」。

## Impact

- **Affected specs**: 新增 delta `console-session`（或等价能力名）描述控制台 HTTP 客户端与租户头的约定。
- **Affected code**: `console/src/requestErrorConfig.ts`（请求拦截器与 401 处理）；可选 `console/README.md`。
- **IAM / 控制面 API**：**无行为变更**；IAM 已支持 `requested_tenant_id == None` 时非平台用户解析为成员列表首租户。

## Non-Goals

- 不在本变更中实现「用户级激活租户持久化」（服务端记住 last tenant）；仍沿用现有 `localStorage` + `ensureTenantSelection`。
- 不修改 IAM `login`/`refresh` 的 OpenAPI 契约。
