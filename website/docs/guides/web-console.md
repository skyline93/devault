---
sidebar_position: 10
title: Web 控制台与 REST 交付节奏（E-UX-001 / 十四-16）
description: 竖切同期闭合或豁免登记；与 OpenAPI、RBAC、CHANGELOG 闸门（十四-17）互链
---

# Web 控制台与 REST 交付节奏（**E-UX-001** / **十四-16**）

## 原则

凡涉及 **§十四**（多 Agent / 多租户执行隔离）及人机控制台相关能力：

1. **同一发布周期**内尽量 **竖切交付**：**REST（OpenAPI）** 与 **`console/`（Ant Design Pro；人机 **Cookie 会话** + 可选 **Bearer**）** 同期上线。
2. 若当次变更 **仅合并 API**（无控制台变更），必须在 **PR 描述**中登记 **豁免**：原因、计划中的 UI 回填、目标截止或跟踪 issue；并更新本页 **[豁免台账](#豁免台账)**（或链接到 issue 后在本页只保留一行摘要）。
3. **用户可见行为**（新字段、新 Job 类型、RBAC 语义变化）必须写入 **`CHANGELOG.md`** 的 **`[Unreleased]`**（见仓库根 **`CONTRIBUTING.md`**）。

与 **十四-17**（OpenAPI ↔ **`console/`**、**auditor** 只读、CI 校验）共用 **`CONTRIBUTING.md`** 与 **`.github/pull_request_template.md`** 清单。CI 在 **`pytest`** 前导出 **`openapi.json`**，运行 **`python scripts/verify_console_openapi_contract.py`**（**无 `/ui` 路径**；**`JobOut` / `PolicyOut`**；**`AuthSessionOut.needs_mfa`**；**`TenantOut.require_mfa_for_admins`**；**§十六** 扩展 **`/api/v1/auth/*`** 路径），再在 **`console/`** 执行 **`npm run codegen`** 与 **`npm run build`**。

## 豁免台账

| 能力域 | 状态 | 说明 / 跟踪 |
|--------|------|-------------|
| §十四 · 01～14 与控制台 | **已同期** | 能力在 **`console/`** 路由与 **`/api/v1/*`** 对齐（十五-11～十八）；历史 Jinja **`/ui/*`** 已于 **十五-19** 下线。 |
| 后续仅 API 变更 | — | 出现时在 PR 登记并追加一行上表。 |

## Ant Design Pro / 会话契约（十五-01～06 + §十六 P0）

企业形态控制台（**`console/`**，见仓库根 **`console/README.md`**）为 **Umi 4（`@umijs/max`）+ Ant Design Pro**，调用 **`/api/v1/*` REST**。人机主路径：**`credentials: 'include'`** + **`POST /api/v1/auth/login`**（**httpOnly** 会话 Cookie，服务端 **Redis**）；自动化与应急使用 **`Authorization: Bearer`**（**`localStorage`**，登录页 **「API Token」** 分栏）。可选 **`X-DeVault-Tenant-Id`**（**`console/src/constants/storage.ts`**）。

1. **会话主体（十五-01 / §十六-06 + P1）**：**`getInitialState`** 先以 **Cookie** 请求 **`GET /api/v1/auth/session`**，失败且存在 **`localStorage`** Bearer 时再带 **`Authorization`** 重试。响应含 **`role`**、**`principal_label`**、**`allowed_tenant_ids`**，以及 **`principal_kind`**、人机时的 **`user_id` / `email` / `tenants`**、**`needs_mfa`**（**§十六-09**：密码登录后若租户要求 **TOTP** 且会话尚未验证，则为 **`true`**；此时 **`canWrite`/`canAdmin`** 为 **`false`** 直至 **`POST /api/v1/auth/mfa/verify`**）。写操作前由 **`GET /api/v1/auth/csrf`**（或登录响应）建立可读 **`devault_csrf`** Cookie；**`request` 拦截器**对 **POST/PUT/PATCH/DELETE** 附加 **`X-CSRF-Token`**。平台 **admin 全租户** 时 **`allowed_tenant_ids`** 为 **`null`**。
2. **OpenAPI → TypeScript（十五-02）**：**`python scripts/export_openapi_json.py -o console/openapi.json`**，再在 **`console/`** 执行 **`npm run codegen`**（或 **`npm run codegen:full`**）。类型输出 **`console/src/openapi/api-types.d.ts`**。
3. **工程与登录（十五-03～06 + §十六 P0/P1）**：**`npm run dev`**（**`/api`** 代理到 **`127.0.0.1:8000`**）。**人机主路径**：**`/user/login`** — **邮箱 + 密码**，需要时同页 **TOTP 第二步**（**`/api/v1/auth/mfa/verify`**）。**机器 / 应急 Bearer**：**`/user/integration`**（与密码页分离，仍写 **`localStorage`**）。可选 **自助注册** **`/user/register`**（后端 **`DEVAULT_CONSOLE_SELF_REGISTRATION_ENABLED=true`**）；**密码重置** **`/user/reset-password?token=`**（邮件内链接须配置 **`DEVAULT_PASSWORD_RESET_LINK_BASE`** 等，见 [配置参考](../admin/configuration.md)）。**`access.ts`**：**`canAdmin` / `canWrite` / `isAuditor`** 在 **`needs_mfa`** 时关闭写/管权限。生产 **HTTPS** 下启用 **`DEVAULT_SESSION_COOKIE_SECURE=true`** 并配置 **`SameSite`**（**`DEVAULT_SESSION_COOKIE_SAMESITE`**）。CI：**导出 OpenAPI** → **`verify_console_openapi_contract.py`**（含 **auth** 扩展路径、**`needs_mfa`**、**`TenantOut.require_mfa_for_admins`**）→ **`npm run build`**。
4. **租户与代理（十五-07～08）**：顶栏 **`TenantSwitcher`** 调 **`GET /api/v1/tenants`**，将所选租户 UUID 写入 **`localStorage`**（**`devault_tenant_id`**），请求拦截器注入 **`X-DeVault-Tenant-Id`**。开发代理另包含 **`/docs`**、**`/metrics`**、**`/version`**、**`/healthz`** 等同源路径。生产同域：**`deploy/nginx/console-spa.conf`**（Compose **`console`** 服务，**十五-21** **`deploy/Dockerfile.console`**）；Helm 可选 **`console.enabled`**（Ingress 拆分 **`/api`** 等与 **`/`** SPA）。
5. **布局与工作台（十五-09～10）**：侧栏 **五大分组**（概览 / 备份与恢复 / 执行面 / 合规与演练 / 平台管理）；顶栏 **环境标签**（**`UMI_APP_ENV_LABEL`**，见 **`console/.env.example`**）与 **帮助** 下拉（新窗打开 **`/docs`**、**`/metrics`**、**`/version`**、**`/healthz`**）。整体 **ProLayout** 与官方模板一致（**`mix`**、**`RightContent` / `AvatarDropdown` / `DefaultFooter`**、**`menuItemRender`+`Link`**，无 **`bgLayoutImgList`** / **`SettingDrawer`**）；**`/overview/welcome`** 为欢迎页，**`/overview/workbench`** 聚合 **`GET /version`** 与 **`GET /api/v1/jobs`** 中最近失败/进行中作业（完整作业中心见十五-11）。

6. **十五-11～十八（与 REST 竖切）**：以下路径均在 **`console/`** SPA 内（Cookie 和/或 Bearer + **`X-DeVault-Tenant-Id`**），与 **`openapi.json`** 中 **`/api/v1/*`** 一致；**`auditor`** 仅只读（无写按钮）；**`admin`** 独占菜单 **平台管理**（**`/platform/tenants`**）及制品 **Legal hold**、舰队 **Enrollment / 吊销 gRPC** 等。未登录：**`/user/login`**、**`/user/integration`**、**`/user/register`**、**`/user/reset-password`**、**`/user/accept-invite`**（§十六-11 邀请接受）。**租户管理员** 可见 **概览 · 成员邀请**（**`/overview/team-invitations`**，`access.canInviteMembers`），对应 **`POST/GET /api/v1/tenants/{tenant_id}/invitations`**。
   - **备份与恢复**：**`/backup/jobs`**、**`/backup/policies`**（含 **`/new`** 与 **`:policyId`**）、**`/backup/run`**、**`/backup/precheck`**、**`/backup/artifacts`**
   - **合规与演练**：**`/compliance/schedules`**、**`/compliance/restore-drill-schedules`**
   - **执行面**：**`/execution/tenant-agents`**、**`/execution/agent-pools`**（含 **`:poolId`** 成员页）、**`/execution/fleet`**（含 **`:agentId`** 详情）
   - **平台管理**（admin）：**`/platform/tenants`**

7. **十五-22～二十四（E2E、列表 query、向导与观测入口）**：**Playwright** 见 **`console/e2e/`** 与 **`.github/workflows/console-e2e.yml`**（**`deploy/docker-compose.console-e2e.yml`**）；**`GET /api/v1/jobs`** 支持 **`kind`/`status`**；**`/backup/run`** 三步向导；工作台 **Grafana`/metrics`** 与 **`UMI_APP_GRAFANA_URL`**（**`console/.env.example`**）。

8. **§十六 P2（企业集成）**：平台 **租户** 编辑表单可维护 **租户级 OIDC**（**issuer + audience** 与 JWT **`iss`/`aud`** 匹配）及 **SAML 元数据登记**（控制面**不解析** SAML 断言；生产可经 IdP 网关换发 OIDC 或使用边缘 OAuth2 过滤器）。**`sso_password_login_disabled`** 与 **`auth/session`** 中 **`tenants[].sso_password_login_disabled`** 提示策略；**仅 SSO** 成员的 **`POST /auth/login`** 返回 **403**。详见 [租户与访问控制](../admin/tenants-and-rbac.md)。

## 相关文档

- [IaC 与批量引导](./iac-bootstrap.md)（**十四-14**）
- [Web 控制台（用户向）](../user/web-console.md)
- [租户与 RBAC](../admin/tenants-and-rbac.md)
- [Agent 舰队](../admin/agent-fleet.md)
