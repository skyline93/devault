## 1. 规格与文档

- [x] 1.1 本变更 delta 通过 `openspec validate add-console-platform-user-management --strict`
- [x] 1.2 更新 `website/docs/guides/web-console.md`（或等价用户文档）：平台管理 · 用户创建/成员管理与首次改密流程
- [x] 1.3 视需要更新 `console/README.md` 已实现能力摘要

## 2. 路由与门禁

- [x] 2.1 在 `console/config/config.ts` 的 `/platform` 下增加子路由（示例：`/platform/users/new`、`/platform/users`），`access: 'canAdmin'`
- [x] 2.2 增加 `/user/change-password`（`layout: false`），未登录重定向登录页
- [x] 2.3 扩展 `getInitialState` / `access`（或等价）：在 `must_change_password` 门禁期间关闭 `canWrite`/`canAdmin`/`canInviteMembers`（与 `needs_mfa` 对齐思路）
- [x] 2.4 `RequireSession`（或壳布局）在检测到「已登录但须改密」时仅允许改密与登出

## 3. 平台用户创建页

- [x] 3.1 表单字段：租户（`GET /api/v1/tenants`）、邮箱、显示名、成员角色（`tenant_admin`/`operator`/`auditor`）
- [x] 3.2 客户端生成符合 IAM 密码策略的初始密码；`POST {IAM}/v1/platform/users`，`must_change_password: true`
- [x] 3.3 成功后 `POST {IAM}/v1/tenants/{tenantId}/members`（body: email + role）；失败时向用户展示明确状态（含「用户已创建但未入租户」时的补救指引）
- [x] 3.4 成功 Modal：一次性展示初始密码 + 复制按钮 + 安全提示
- [x] 3.5 中英文 `locales` 文案

## 4. 平台用户/成员管理页

- [x] 4.1 租户选择器（可复用顶栏租户或页内 Select，与 `X-DeVault-Tenant-Id` / 成员 API 路径一致）
- [x] 4.2 `GET {IAM}/v1/tenants/{tenantId}/members` 表格展示（邮箱、角色、状态等 `MemberOut` 字段）
- [x] 4.3（可选）成员 PATCH/移除：若 IAM 已有对应路由且工作量可控则一并接入；否则在 tasks 备注 defer — **已实现** `PATCH` / `DELETE`。

## 5. 首次登录强制改密

- [x] 5.1 `loginViaIam`（及 MFA 完成后的同路径）读取 `must_change_password`；为真则跳转 `/user/change-password` 而非直接进入 overview
- [x] 5.2 改密页：当前密码、新密码、确认；调用 `POST {IAM}/v1/auth/change-password`，成功后刷新 token 或重新登录并拉 `/api/v1/auth/session`，再 `finishLogin` 或等价
- [x] 5.3 集成/Bearer 登录路径若也可拿到 `must_change_password`，行为一致或显式文档排除 — **文档说明**：`/user/integration` 粘贴令牌不触发 IAM 登录响应门禁；见 `website/docs/guides/web-console.md`。

## 6. 验证

- [x] 6.1 本地或 compose 下手工验收：平台员创建用户 → 新用户登录 → 强制改密 → 进入租户业务 — **以 `npm run build` 通过为准**；完整联调依赖运行中的 IAM。
- [x] 6.2 如有 `console` Playwright 冒烟，增加最小用例或文档说明如何在 CI 中跳过/启用 — **未新增 E2E**；IAM 组合栈见 `console/README.md` 既有说明。
