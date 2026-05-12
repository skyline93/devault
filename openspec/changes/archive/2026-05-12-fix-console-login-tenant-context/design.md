## Context

- IAM：`iam/src/devault_iam/api/routes/auth.py` 将 `body.tenant_id` 与 `X-DeVault-Tenant-Id` / `X-Tenant-Id` 合并为 `requested`；`resolve_effective_tenant_for_login` 对平台管理员在 `requested != None` 时拒绝（`platform_user_tenant_disallowed`），对租户用户在校验失败时返回 `tenant_not_allowed`。
- Console：`console/src/requestErrorConfig.ts` 在存在 `devault_tenant_id` 时为**所有**请求附加租户头；`AvatarDropdown` 退出时已清除租户，但 **401** 路径此前仅清除 Bearer。

## Goals

- 登录请求不得因**陈旧或错误**的本地租户 ID 而失败。
- 与现有「登录成功后由 `ensureTenantSelection` 校正租户」流程兼容。

## Decisions

1. **按 URL 排除租户头**（相对 `IAM_API_PREFIX` 或显式匹配 `/v1/auth/login`、`/v1/auth/refresh`）：实现简单、与「仅 Console 调 IAM 登录」现状一致；未来若有其它 IAM 调用需租户头，再收窄/白名单。
2. **401 时同时清除 `STORAGE_TENANT_ID_KEY`**：与会话失效语义一致，避免下一次 IAM 登录携带脏头。

## Risks / Trade-offs

- **Refresh**：若将来依赖「刷新时切换租户」且仅通过 header 传租户，本排除逻辑需与 refresh 调用方式对齐；当前 refresh 若由同一拦截器发起，排除 header 与「无请求体租户」时行为与 IAM 默认首租户一致，平台管理员亦需要无头 refresh。

## Migration Plan

- 纯前端与文档；无数据迁移。部署后用户重新登录即可。
