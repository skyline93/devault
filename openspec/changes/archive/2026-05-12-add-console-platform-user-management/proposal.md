# Change: 控制台平台管理 — 用户创建、租户绑定与首次改密

## Why

平台管理员需要在控制台内完成「创建 IAM 用户、将其加入指定租户、发放一次性初始密码」，而不依赖邮件邀请或仅依赖 CLI。同时，管理员创建的账户应在首次登录时被强制修改密码，以降低初始凭据泄露风险。当前控制台缺少上述入口；IAM 已具备 `POST /v1/platform/users`、`POST /v1/tenants/{tenant_id}/members`、`must_change_password` 与 `POST /v1/auth/change-password` 等能力，但控制台未串联完整人机流程。

## What Changes

- 在 **平台管理** 菜单下增加 **创建用户**（含租户选择、成员角色、初始密码生成与一次性展示）与 **用户/成员管理**（按所选租户列出 IAM 成员，支持后续扩展维护操作）。
- 创建流程 **不**使用控制面邮件邀请 API；顺序为：IAM 创建用户（`must_change_password: true`）→ IAM 将同一邮箱加入所选租户成员。
- **IAM 登录路径**：当 `POST …/v1/auth/login` 响应中 `must_change_password` 为真时，控制台 **MUST** 在进入业务页面前引导用户完成 IAM **改密**（`POST …/v1/auth/change-password`），改密成功后再建立与现有一致的控制面会话体验。
- 文档与（如适用）E2E/冒烟用例覆盖上述行为；**不**改变非平台用户既有登录与租户选择主体流程。

## Impact

- **Affected specs（delta）**: `console-session`（强制改密门禁与改密页）；新增 delta 能力 **`console-platform-user-management`**（平台侧用户与成员 UI 行为）。
- **Affected code（预期）**: `console/config/config.ts`（路由与 `canAdmin`）、`console/src/pages/platform/*`（新页）、`console/src/pages/user/login/*`、`console/src/app.tsx` / `require-session` 或等价门禁、`console/src/locales/*`；可选 `website/docs/guides/web-console.md` 等用户文档。
- **IAM / 控制面**: 以现有公开 API 为准；若实现中发现列表类缺口（例如需 `GET /v1/platform/users`），在实现阶段以本变更 `tasks.md` 与 `design.md` 的决策为准是否扩展 IAM。
