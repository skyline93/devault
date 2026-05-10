---
sidebar_position: 10
title: Web 控制台与 REST 交付节奏（E-UX-001 / 十四-16）
description: 竖切同期闭合或豁免登记；与 OpenAPI、RBAC、CHANGELOG 闸门（十四-17）互链
---

# Web 控制台与 REST 交付节奏（**E-UX-001** / **十四-16**）

## 原则

凡涉及 **§十四**（多 Agent / 多租户执行隔离）及人机控制台相关能力：

1. **同一发布周期**内尽量 **竖切交付**：**REST（OpenAPI）** 与 **`console/`（Ant Design Pro + Bearer）** 同期上线。
2. 若当次变更 **仅合并 API**（无控制台变更），必须在 **PR 描述**中登记 **豁免**：原因、计划中的 UI 回填、目标截止或跟踪 issue；并更新本页 **[豁免台账](#豁免台账)**（或链接到 issue 后在本页只保留一行摘要）。
3. **用户可见行为**（新字段、新 Job 类型、RBAC 语义变化）必须写入 **`CHANGELOG.md`** 的 **`[Unreleased]`**（见仓库根 **`CONTRIBUTING.md`**）。

与 **十四-17**（OpenAPI ↔ **`console/`**、**auditor** 只读、CI 校验）共用 **`CONTRIBUTING.md`** 与 **`.github/pull_request_template.md`** 清单。CI 在 **`pytest`** 前导出 **`openapi.json`**，运行 **`python scripts/verify_console_openapi_contract.py`**（**无 `/ui` 路径**；**`JobOut` / `PolicyOut`** 关键字段存在），再在 **`console/`** 执行 **`npm run codegen`** 与 **`npm run build`**。

## 豁免台账

| 能力域 | 状态 | 说明 / 跟踪 |
|--------|------|-------------|
| §十四 · 01～14 与控制台 | **已同期** | 能力在 **`console/`** 路由与 **`/api/v1/*`** 对齐（十五-11～十八）；历史 Jinja **`/ui/*`** 已于 **十五-19** 下线。 |
| 后续仅 API 变更 | — | 出现时在 PR 登记并追加一行上表。 |

## Ant Design Pro / Bearer 契约（十五-01～06）

企业形态控制台（**`console/`**，见仓库根 **`console/README.md`**）为 **Umi 4（`@umijs/max`）+ Ant Design Pro**，仅调用 **`/api/v1/*` REST**，使用 **`Authorization: Bearer`** 与可选 **`X-DeVault-Tenant-Id`**（见 **`console/src/constants/storage.ts`**）。

1. **会话主体（十五-01）**：**`getInitialState`** 请求 **`GET /api/v1/auth/session`**，响应含 **`role`**、**`principal_label`**、**`allowed_tenant_ids`**（**admin 全租户**时为 **`null`**）。平台启用认证且无有效 Bearer 时 **401**；令牌无效 **403**。
2. **OpenAPI → TypeScript（十五-02）**：**`python scripts/export_openapi_json.py -o console/openapi.json`**，再在 **`console/`** 执行 **`npm run codegen`**（或 **`npm run codegen:full`**）。类型输出 **`console/src/openapi/api-types.d.ts`**。
3. **工程与登录（十五-03～06）**：**`npm run dev`** 启动开发服务器（默认 **`http://localhost:8010`**，与 **`uvicorn :8000`** 错开；**`/api`** 代理到 **`127.0.0.1:8000`**）；**`/user/login`** 使用表单录入 Token 并写入 **`localStorage`**（**非** HTTP Basic）；**`request` 拦截器**统一带头；**`access.ts`** 暴露 **`canAdmin` / `canWrite` / `isAuditor`**。CI 在 pytest 矩阵中执行导出 + **`verify_console_openapi_contract.py`** + **`npm run build`**，与 **十四-17** 互补。
4. **租户与代理（十五-07～08）**：顶栏 **`TenantSwitcher`** 调 **`GET /api/v1/tenants`**，将所选租户 UUID 写入 **`localStorage`**（**`devault_tenant_id`**），请求拦截器注入 **`X-DeVault-Tenant-Id`**。开发代理另包含 **`/docs`**、**`/metrics`**、**`/version`**、**`/healthz`** 等同源路径。生产同域：**`deploy/nginx/console-spa.conf`**（Compose **`console`** 服务，**十五-21** **`deploy/Dockerfile.console`**）；Helm 可选 **`console.enabled`**（Ingress 拆分 **`/api`** 等与 **`/`** SPA）。
5. **布局与工作台（十五-09～10）**：侧栏 **五大分组**（概览 / 备份与恢复 / 执行面 / 合规与演练 / 平台管理）；顶栏 **环境标签**（**`UMI_APP_ENV_LABEL`**，见 **`console/.env.example`**）与 **帮助** 下拉（新窗打开 **`/docs`**、**`/metrics`**、**`/version`**、**`/healthz`**）。整体 **ProLayout** 与官方模板一致（**`mix`**、**`RightContent` / `AvatarDropdown` / `DefaultFooter`**、**`menuItemRender`+`Link`**，无 **`bgLayoutImgList`** / **`SettingDrawer`**）；**`/overview/welcome`** 为欢迎页，**`/overview/workbench`** 聚合 **`GET /version`** 与 **`GET /api/v1/jobs`** 中最近失败/进行中作业（完整作业中心见十五-11）。

6. **十五-11～十八（与 REST 竖切）**：以下路径均在 **`console/`** SPA 内（Bearer + **`X-DeVault-Tenant-Id`**），与 **`openapi.json`** 中 **`/api/v1/*`** 一致；**`auditor`** 仅只读（无写按钮）；**`admin`** 独占菜单 **平台管理**（**`/platform/tenants`**）及制品 **Legal hold**、舰队 **Enrollment / 吊销 gRPC** 等。
   - **备份与恢复**：**`/backup/jobs`**、**`/backup/policies`**（含 **`/new`** 与 **`:policyId`**）、**`/backup/run`**、**`/backup/precheck`**、**`/backup/artifacts`**
   - **合规与演练**：**`/compliance/schedules`**、**`/compliance/restore-drill-schedules`**
   - **执行面**：**`/execution/tenant-agents`**、**`/execution/agent-pools`**（含 **`:poolId`** 成员页）、**`/execution/fleet`**（含 **`:agentId`** 详情）
   - **平台管理**（admin）：**`/platform/tenants`**

7. **十五-22～二十四（E2E、列表 query、向导与观测入口）**：**Playwright** 见 **`console/e2e/`** 与 **`.github/workflows/console-e2e.yml`**（**`deploy/docker-compose.console-e2e.yml`**）；**`GET /api/v1/jobs`** 支持 **`kind`/`status`**；**`/backup/run`** 三步向导；工作台 **Grafana`/metrics`** 与 **`UMI_APP_GRAFANA_URL`**（**`console/.env.example`**）。

## 相关文档

- [IaC 与批量引导](./iac-bootstrap.md)（**十四-14**）
- [Web 控制台（用户向）](../user/web-console.md)
- [租户与 RBAC](../admin/tenants-and-rbac.md)
- [Agent 舰队](../admin/agent-fleet.md)
