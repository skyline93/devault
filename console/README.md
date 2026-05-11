# DeVault 企业控制台（Ant Design Pro · Umi 4 · §十五）

前后端分离的 **Ant Design Pro（`@umijs/max` 4 + `antd` 5 + `@ant-design/pro-components` 2）** 工程，调用控制面 **`/api/v1/*`**。人机主路径：**Cookie 会话**（**`credentials: 'include'`** + **`POST /api/v1/auth/login`**）；**`Authorization: Bearer`** + **`X-DeVault-Tenant-Id`** 仍用于 API 密钥 / 自动化（§十六）。与文档站 **`website/`** 目录分离。

**布局**：以 [Ant Design Pro 官方仓库](https://github.com/ant-design/ant-design-pro) 的 **`defaultSettings` + `RunTimeLayoutConfig`** 为蓝本（`mix` 顶栏 + 侧栏、**`menuItemRender` + `Link`**、**`RightContent` / `AvatarDropdown` / `DefaultFooter`**）；**精简**（无 `bgLayoutImgList`、无 `SettingDrawer`、无外链 logo）。业务逻辑（会话、租户、帮助、工作台）挂在官方推荐的顶栏右侧组合上。

**国际化（需求与验收）**：默认英文、界面内切换简体中文、不跟随系统语言、可扩展更多语言；优先 **Ant Design / Umi Max** 惯用方案，用户向文案须正式且不得暴露内部设计术语。详见 [`docs/web-console-i18n.md`](../docs/web-console-i18n.md)。

## 先决条件

- **Node.js ≥ 20**（推荐 22，与 CI 一致）。
- 仓库根已 **`pip install -e ".[dev]"`**（或等价 venv），用于 **`npm run export-openapi`**。
- 可选：复制 **`console/.env.example`** 为 **`.env`**，设置 **`UMI_APP_ENV_LABEL`**（顶栏环境标识，十五-09）。

## 常用命令

| 命令 | 说明 |
|------|------|
| `npm run dev` | 本地开发（默认 **`http://localhost:8010`**；**`proxy`** 将 **`/api`**、**`/openapi.json`**、**`/docs`**、**`/redoc`**、**`/metrics`**、**`/version`**、**`/healthz`** 转到 **`http://127.0.0.1:8000`**；可选 **`/iam-api`** → **`http://127.0.0.1:8100`** 独立 IAM，见 **`.env.example`** 的 **`UMI_APP_IAM_PREFIX`**）。 |
| `npm run build` | 生产静态资源输出到 **`dist/`**（CI 用其做类型与打包校验）。 |
| `npm run export-openapi` | 写出 **`openapi.json`**（勿提交，已 `.gitignore`）。 |
| `npm run codegen` | **`openapi-typescript`** → **`src/openapi/api-types.d.ts`**。 |
| `npm run codegen:full` | 导出 + codegen（需 **`python3`**）。 |
| `npm run preview` | 本地预览 **`dist/`**（默认端口 **8001**）。 |
| `npm run test:e2e` | **Playwright** 冒烟（**十五-22**）；需已启动控制面 + 控制台（推荐 **`deploy/docker-compose.console-e2e.yml`**），默认 **`E2E_BASE_URL=http://127.0.0.1:8080`**、**`E2E_API_ORIGIN=http://127.0.0.1:8000`**。未设置 **`E2E_API_TOKEN`** 时假定控制面 **dev-open**；若控制面已配置 IAM，请设置有效 JWT。首次需 **`npx playwright install chromium`**。 |

首次 **`npm install`** 会执行 **`max setup`**（**`postinstall`**），生成 **`src/.umi`** 等本地文件（已 `.gitignore`）。

## 已实现能力摘要

### 十五-01～06（基座）+ IAM 人机身份

- 会话、OpenAPI 类型、**`/user/login`**（**IAM** 或历史邮箱 UI）、**`/user/integration`**（**IAM access_token** 或 dev-open 留空）、**`/user/register`**（IAM 模式）；**`request` 拦截器**（可选 **`X-CSRF-Token`** 若浏览器仍有旧 Cookie、**`credentials: 'include'`**）；**`getInitialState` / `access.ts`**（**`needs_mfa`** 时关闭 **`canWrite`/`canAdmin`/`canInviteMembers`**）。

### 十五-07（租户）

- 顶栏 **`TenantSwitcher`**：**`GET /api/v1/tenants`**（列表已由控制面按 token 过滤）；非 admin 再按 **`allowed_tenant_ids`** 客户端收窄；所选 UUID 写入 **`localStorage`**（**`devault_tenant_id`**），切换后整页刷新以拉取新租户数据。
- **`getInitialState`** 内 **`ensureTenantSelection`**：若无合法已存租户，则默认选列表第一项。
- 控制面已下线 Jinja **`/ui/*`**；租户上下文仅 **`localStorage`** + **`X-DeVault-Tenant-Id`**（十五-19）。

### 十五-08（代理与部署）

- **开发**：见 **`config/config.ts`** **`proxy`**。
- **生产同域**：**`deploy/nginx/console-spa.conf.template`**（Docker 镜像用 **envsubst**：**`DEVAULT_CONSOLE_API_UPSTREAM`**、**`DEVAULT_CONSOLE_IAM_UPSTREAM`**）；静态参考 **`deploy/nginx/console-spa.conf`**。
- **Compose（可选 · 十五-21）**：在 **`deploy/`** 执行 **`docker compose --profile with-console build console && docker compose --profile with-console up -d`**（多阶段 **`deploy/Dockerfile.console`**，无需主机预建 **`dist/`**），访问 **`http://127.0.0.1:8080/`**。
- **Helm**：**`console.enabled: true`** 时安装控制台 Deployment/Service，Ingress 将 **`/api`**、**`/docs`** 等指向 API，**`/`** 指向控制台（见 **`deploy/helm/devault/values.yaml`**）。

### 十五-19～二十一（闸门与镜像）

- **CI 契约**：**`scripts/verify_console_openapi_contract.py`**（在导出 **`openapi.json`** 后运行）。
- **镜像**：**`deploy/Dockerfile.console`**（仓库根为 **`docker build` context）。

### 十五-22～二十四（E2E、作业 query、向导与观测）

- **E2E**：**`e2e/smoke.spec.ts`**；CI **`.github/workflows/console-e2e.yml`**；本地栈 **`deploy/docker-compose.console-e2e.yml`**（**`docker compose -f deploy/docker-compose.console-e2e.yml up -d --build`**，仓库根或 **`deploy/`** 下执行）。
- **作业列表**：**`GET /api/v1/jobs?kind=&status=`** 与作业中心 **`ProTable`** 联动（**十五-23**）。
- **发起备份**：**`/backup/run`** 分步 **Steps** 向导（**十五-24**）；工作台 **Grafana / `/metrics`** 见 **`UMI_APP_GRAFANA_URL`**（**`.env.example`**）。

### 十五-09（信息架构与顶栏）

- 侧栏 **五大分组**：概览、备份与恢复、执行面、合规与演练、平台管理；子路由见 **`config/config.ts`**。
- 顶栏 **环境标签**（**`UMI_APP_ENV_LABEL`**）、**帮助** 下拉（新窗 **`/docs`**、**`/metrics`**、**`/version`**、**`/healthz`**）。

### 十五-10（工作台）

- 路由 **`/overview/workbench`**：**`GET /version`** 卡片 + **`GET /api/v1/jobs`** 中最近 **失败 / 进行中** 作业简表；链至 **`/backup/jobs`** 完整作业中心。

### 十五-11～十八（租户主路径 + 执行面 + 平台）

- **备份与恢复**：**`/backup/jobs`**（筛选、取消/重试、详情抽屉）；**`/backup/policies`**、**`/backup/policies/new`**、**`/backup/policies/:policyId`**（Tab 表单 **`FileBackupConfigV1`**、执行绑定、内嵌备份计划）；**`/backup/run`**、**`/backup/precheck`**；**`/backup/artifacts`**（分页、恢复/演练二次确认、管理员 Legal hold）。
- **合规与演练**：**`/compliance/schedules`**、**`/compliance/restore-drill-schedules`**（全 CRUD）。
- **执行面**：**`/execution/tenant-agents`**；**`/execution/agent-pools`**、**`/execution/agent-pools/:poolId`**（成员 **PUT**）；**`/execution/fleet`**、**`/execution/fleet/:agentId`**（Enrollment、吊销 gRPC）。
- **平台管理**（仅 **`access.canAdmin`** 见菜单）：**`/platform/tenants`**（**`TenantPatch`** 表单）。
- **RBAC**：写操作依赖 **`canWrite`**；Legal hold、Enrollment、吊销、gRPC 吊销、租户 PATCH 依赖 **`canAdmin`**；**auditor** 与 **`isAuditor`** 对齐只读。

## 会话 API（十五-01）

**`GET /api/v1/auth/session`** 返回 **`role`**、**`principal_label`**、**`allowed_tenant_ids`**，以及 **`principal_kind`**（**`platform` \| `tenant_user`**）、IAM 人机时的 **`user_id` / `tenants`**、**`needs_mfa`**。平台 admin 全租户时 **`allowed_tenant_ids`** 为 **`null`**。控制面仅保留该认证相关 HTTP 路由；登录/注册/MFA/邀请等在 **IAM** 完成。

**IAM**：构建时设置 **`UMI_APP_IAM_PREFIX=/iam-api`**（与 `config/config.ts` 开发代理一致）后，登录/注册请求发往 IAM（**`/iam-api/v1/auth/*`**），成功后把 **`access_token`** 写入 **`devault_bearer_token`** 并调用 DeVault **`GET /api/v1/auth/session`**（需控制面配置 **`DEVAULT_IAM_JWT_ISSUER`**、**`DEVAULT_IAM_JWT_AUDIENCE`** 与 JWKS 或 PEM，见 [`docs/iam-service-design.md`](../docs/iam-service-design.md)）。

## 存储键

| 键 | 用途 |
|----|------|
| **`devault_bearer_token`** | 可选：保存 IAM **`access_token`** 作为 Bearer；**密码登录**成功后会清除，避免人机长期依赖 localStorage。 |
| **`devault_tenant_id`** | 当前租户 UUID（顶栏选择器写入 **`X-DeVault-Tenant-Id`**）。 |
