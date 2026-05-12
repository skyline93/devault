## 1. Implementation

- [x] 1.1 在 `console/src/requestErrorConfig.ts` 中：对发往 IAM 前缀的请求（`IAM_API_PREFIX` 非空且 URL 以该前缀开头），**不**设置 `X-DeVault-Tenant-Id`；或等价地仅对 `/v1/auth/login` 与 `/v1/auth/refresh` 排除租户头（二选一，以保持与现有 `IAM_API_PREFIX` 配置一致为准）。
- [x] 1.2 在同一文件的 401 处理分支中，在移除 `STORAGE_BEARER_KEY` 的同时 **`localStorage.removeItem(STORAGE_TENANT_ID_KEY)`**。
- [x] 1.3 手动验证：本地 `devault_tenant_id` 设为与当前登录用户无关的 UUID 后，IAM 登录仍可成功；平台管理员在残留租户下登录成功；401 重定向登录后不再携带错误租户头。

## 2. Documentation

- [x] 2.1 更新 `console/README.md` 中与「租户头 / 登录」相关的段落，说明 IAM 登录与刷新不携带 `X-DeVault-Tenant-Id` 的约定及原因。
- [x] 2.2 更新根目录 **`CHANGELOG.md`**（**`[Unreleased]` → Fixed**）与 **`website/docs/guides/web-console.md`**、**`website/docs/user/web-console.md`**、**`website/docs/trust/api-access.md`** 中与租户头 / IAM 登录一致的描述。

## 3. Quality

- [x] 3.1 运行 `openspec validate fix-console-login-tenant-context --strict` 并修复校验问题（若 CI 已挂载）。
