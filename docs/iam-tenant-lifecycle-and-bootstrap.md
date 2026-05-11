# IAM 租户生命周期与平台引导（无默认租户 · 无自助注册）

本文档记录 **目标态设计** 与 **落地任务清单**：与 [`docs-old/iam.md`](../docs-old/iam.md) 中「Platform ≠ Tenant」「平台管理员零租户 membership」「租户由平台创建」「普通用户无自助注册」等原则对齐；并与 [`docs/iam-service-design.md`](iam-service-design.md) 中独立 IAM 职责边界一致。

**本文档为规格说明**；实现以代码与 [`iam/docs/BACKLOG.md`](../iam/docs/BACKLOG.md) 为准。**按优先级的实现拆解见 §12**；完成后应回写 BACKLOG、§15 修订记录与相关用户文档。

**兼容性策略**：本规格**不要求**与旧版数据、旧环境变量或已删除 API **向后兼容**。实现以 **删除旧路径与旧假设**（默认租户、自助注册、`platform_admin` membership 等）为准，**不提供**双轨运行、迁移期回落开关或「仅 legacy 可用」的并行行为。

---

## 1. 文档目的与范围

| 项 | 说明 |
|----|------|
| **目的** | 统一团队对「无默认租户、仅平台管理员建租户、用户由管理员发放、引导用独立 CLI、演示栈单独初始化」的约定，便于评审与分阶段实现。 |
| **范围** | IAM（`iam/`）、Console 认证入口、DeVault 控制面租户解析与 Agent enrollment 文档/演示；**不包含** Agent gRPC 协议本身变更。 |
| **非目标** | 不在本文替换 [`docs-old/iam.md`](../docs-old/iam.md) 全文；不规定具体 UI 线框图。 |

---

## 2. 设计原则（验收口径）

1. **无默认租户**  
   - 迁移/种子 **不**再插入 `slug=default`（或等价「占位租户」）作为产品假设。  
   - 任意租户 **仅** 由具备平台管理能力的主体创建（见 §8）。

2. **平台管理员：用户标志位**  
   - 使用 **`users.is_platform_admin`**（布尔，默认 `false`）。  
   - 平台管理员 **不得** 拥有任何 `tenant_members` 行（零租户 membership）。  
   - 平台能力与权限通过 **独立分支** 签发 JWT / 构造 `Principal`（仅包含 `devault.platform.*` 等约定权限），**不**通过「把 `platform_admin` 角色写进某租户的 membership」模拟。

3. **普通用户：无自助注册**  
   - 关闭面向匿名用户的注册入口与 API。  
   - 账号由平台管理员（或后续可扩展的自动化）创建；分配初始凭据与 **租户 + 角色**（`tenant_members`）。

4. **首次引导：独立 CLI**  
   - **不**在 IAM 应用进程启动时自动创建首个平台管理员（避免竞态、误配、密钥进镜像）。  
   - 由运维在 **空库或首次部署后** 执行 **独立 CLI** 完成首个平台用户创建（见 §6）。

5. **演示栈 / 本地开发**  
   - **不**把「创建演示租户、演示用户、Agent enrollment」写进主业务启动路径。  
   - 通过 **额外初始化步骤**（脚本或 compose `depends_on` + 一次性 job）调用 **正式 HTTP API** 完成；失败可重试，且 **不改变** 生产默认配置语义。

---

## 3. 与当前实现的差异（背景）

当前仓库存在与本文目标态不一致的行为（实现时需逐项清理或迁移）：

| 现状 | 目标 |
|------|------|
| ~~`p0_001` 曾插入 `slug=default` 租户~~ | **已移除**：首迁仅 schema + RBAC 模板，不预置租户行 |
| `register_user` 依赖 `get_default_tenant`，首用户 `platform_admin` 写入 `tenant_members` | **删除**该路径；平台员仅用 `is_platform_admin` |
| `POST /v1/auth/register` + Console 自助注册页 | **删除**路由与页面；**删除** `self_registration_enabled` 等开关（不再保留「关闭即可」的双轨） |
| 文档/Compose 假设存在 default 租户与 enrollment 种子 | 演示改为 §9 初始化 API 流 |

---

## 4. 数据模型

### 4.1 `users` 表扩展

| 列 | 类型 | 说明 |
|----|------|------|
| `is_platform_admin` | `BOOLEAN NOT NULL DEFAULT false` | **唯一**平台主体标志；`true` 时禁止存在任何 `tenant_members` 行（应用层必检；可选 DB 触发器/约束见实现 PR）。 |
| `must_change_password` | `BOOLEAN NOT NULL DEFAULT false`（可选） | 管理员创建账户后强制首次改密。 |

**约束建议（应用层必检，DB 可选）**：

- `is_platform_admin = true` ⇒ `NOT EXISTS (SELECT 1 FROM tenant_members WHERE user_id = users.id)`。  
- 若使用 DB 约束，可用触发器或部分唯一索引策略；若暂不实施 DB 层，至少在创建/更新 membership 与设置标志位时双向校验。

### 4.2 `tenants` / `tenant_members`

- **`tenants`**：仅通过平台权限可调用的 `POST /v1/tenants`（或等价路径）创建；`owner_user_id` 可在创建时指定或后续 PATCH。  
- **`tenant_members`**：**仅** 非平台管理员用户；每行表示「某用户在某租户内的 RBAC 模板角色」（`tenant_admin` / `operator` / `auditor` 等，与现有 `roles` 种子对齐）。

### 4.3 系统角色种子

- 保留 **租户侧** 模板角色：`tenant_admin`、`operator`、`auditor`。  
- **`platform_admin` 作为「仅绑定 permission 集合」的全局定义**可保留用于 **权限枚举**，但 **禁止** 再将其 `role_id` 写入 `tenant_members` 表达平台员身份；平台员身份 **仅** `is_platform_admin`。

---

## 5. JWT、`Principal` 与登录语义

### 5.1 平台管理员访问令牌

访问令牌字段约定（以实现为准，与现有 `sub` / `tid` / `perm` / `pk` 等命名对齐即可）：

| Claim / 字段 | 值 |
|----------------|-----|
| `sub` | 用户 UUID |
| `pk` | `platform` |
| `tid` | **省略**或显式 `null`（不得隐式回落到某一业务租户） |
| `tids` | 空数组；列举「全部租户」用独立 **平台 API**（`GET /v1/tenants`），不塞进 JWT 体积 |
| `perm` | 仅平台级 permission keys（如 `devault.platform.admin` 及后续扩展） |
| `mfa` | 与现有一致 |

### 5.2 租户用户访问令牌

| Claim / 字段 | 值 |
|----------------|-----|
| `pk` | `tenant_user` |
| `tid` | 当前工作租户 UUID（必须属于该用户的 `tenant_members`） |
| `perm` | 该租户 membership 对应角色的展开 permission |

### 5.3 登录 API 行为

- **平台管理员**：允许在 **未指定租户** 的情况下登录，签发 §5.1 令牌。  
- **租户用户**：若仅属于一个租户，可直接签发带 `tid` 的令牌；若多租户，必须 **显式** `tenant_id`（请求体或头）。**禁止** 使用 `slug=default` 或任何「默认租户」回落解析。

---

## 6. 独立 CLI：平台引导（Bootstrap）

### 6.1 定位

- **独立入口**：例如 `python -m devault_iam.cli bootstrap` 或 `iam-admin` console script（在 `iam/pyproject.toml` 注册 `console_scripts`）。  
- **运行环境**：与 API 相同的 `IAM_DATABASE_URL`、密码哈希参数；**不**随 `uvicorn` 自动执行。

### 6.2 建议子命令与参数

| 子命令 | 作用 | 幂等性 |
|--------|------|--------|
| `bootstrap create-platform-user` | 若不存在任何 `is_platform_admin=true` 的用户，则创建指定 email 的用户并设 `is_platform_admin=true`、写入 `password_hash`；否则失败并提示已引导 | **幂等**：已存在平台员则拒绝重复执行（不提供与旧数据模型并存的引导模式） |
| `bootstrap status` | 打印是否已存在平台管理员、用户数（不含密码） | 只读 |

**参数示例**：

- `--email`（必填）  
- `--password`（stdin 优先，避免 shell history；或 `--password-file`）  
- `--name`（可选）

### 6.3 安全要求

- 禁止在日志中打印明文密码。  
- 生产环境文档要求：**执行后立即轮换**或使用一次性密码 + `must_change_password`。  
- 审计：写入 IAM `audit_logs`，`action` 如 `platform.bootstrap`。

### 6.4 与「空库」关系

- CLI 假设数据库已完成 **Alembic 迁移**（表存在、RBAC 种子存在）。  
- **不**要求预置租户行。

---

## 7. 关闭自助注册（行为 + 代码清理清单）

### 7.1 产品行为

- **删除** `POST /v1/auth/register` 路由及其实现；客户端命中应 **404**（未注册路径）。  
- **删除** `self_registration_enabled` 及一切「注册开关」配置（不再保留「可关可开」语义）。  
- Console：**删除** `/user/register` 路由、注册页与登录页「自助注册」入口；若需说明，用登录页文案或外链文档「请联系管理员」即可。

### 7.2 代码清理清单（实现 PR 时逐项勾选）

| 状态 | 区域 | 动作 |
|------|------|------|
| [x] | `iam/src/devault_iam/services/auth_service.py` | **删除** `register_user` 及仅被其调用的辅助逻辑 |
| [x] | `iam/src/devault_iam/api/routes/auth.py` | **删除** `post_register` 路由 |
| [x] | `iam/src/devault_iam/settings.py`（等） | **删除** `self_registration_enabled` 及相关分支 |
| [x] | `iam/tests/*` | **删除**依赖自助注册的用例；新建用户一律经 CLI 或 §8 管理 API |
| [x] | `console/src/pages/user/register/*` | **删除**注册页及相关组件 |
| [x] | `console/config/config.ts` | **删除** register 路由 |
| [x] | `console/src/pages/user/login/index.tsx` | **删除**注册链接 |
| [x] | `console/README.md` / i18n | 更新文案与说明 |
| [x] | `docs/iam-service-design.md` §7 API 表 | **删除** register 行或标明「已删除」 |
| [x] | **OpenAPI / 类型** | Console `codegen:full` 针对控制面 **`devault.api.main`**；IAM 无并入该 JSON，无需为删 register 重跑 |

---

## 8. 管理面 API（平台管理员）

以下均需 **平台 JWT**（`is_platform_admin` 签发）鉴权；具体路径可与现有 `tenants` 路由合并或加 `/v1/platform/*` 前缀。

| 能力 | 方法 | 说明 |
|------|------|------|
| 创建租户 | `POST /v1/tenants` | 已存在时需 `devault.platform.admin`；创建后触发 DeVault 镜像（若采用镜像策略） |
| 列举租户 | `GET /v1/tenants` | 平台员全局列表；租户用户仅返回自己有 membership 的租户 |
| 创建用户 | `POST /v1/platform/users`（建议路径） | body：`email`、`name`、`password` 或 `send_invite`（后续）、`must_change_password` |
| 重置密码 / 设 must_change | `PATCH /v1/platform/users/{id}` | 可选 |
| 添加成员 | `POST /v1/tenants/{tenant_id}/members` | 绑定 `user_id` + 模板 `role` |
| 移除成员 | `DELETE ...` | 与现有一致扩展 |

**禁止**：任何公开匿名接口创建用户或租户。

---

## 9. 演示栈与本地开发：额外初始化

### 9.1 原则

- **主镜像 / 主 `docker compose up`**：不自动执行「建租户、建用户、写 enrollment」。  
- **演示 profile**：单独 `compose` override 或 **`deploy/scripts/`** 下初始化脚本，在 **IAM + DeVault 就绪后** 执行。

### 9.2 建议调用顺序（示例）

1. 运维或 CI 已对空库执行 **`iam-admin bootstrap`**（见 §6）。  
2. 初始化脚本使用平台员 **换取 access token**（`POST /v1/auth/login`）。  
3. `POST /v1/tenants` 创建例如 `slug=demo` 租户。  
4. `POST /v1/platform/users` 创建演示租户用户 + `POST .../members` 分配 `tenant_admin` / `operator`。  
5. 调用 **DeVault** `PUT /api/v1/agents/{agent_id}/enrollment`（或项目既有接口）绑定 `demo` 租户 **UUID**。  
6. Agent 使用演示凭据 `Register`（与现有一致）。

### 9.3 与主业务隔离

- 初始化脚本 **仅** 依赖稳定公开 API；不 import 应用内部 ORM。  
- 失败时 **退出非零**，便于 CI 发现；支持 **幂等**（已存在 `slug=demo` 则跳过或 PATCH）。

### 9.4 文档与仓库维护

- 更新 `deploy/docker-compose*.yml` 注释与 `website/docs/user/quickstart.md`、`website/docs/guides/iac-bootstrap.md`：明确「默认无租户；演示需执行初始化脚本」。  
- **删除或改写**迁移与种子中对 **`slug=default` 的硬编码**（如 `0011` 等）：改为由 §9 演示脚本使用 **`demo`**（或约定 slug）租户 UUID 写入 enrollment，**不**再假设库内必有 default。

---

## 10. DeVault 控制面对齐

| 项 | 说明 |
|----|------|
| ~~**`DEVAULT_DEFAULT_TENANT_SLUG` / `default_tenant_slug`**~~ | **已实现**：配置项已移除；租户作用域 API **必须**携带 **`X-DeVault-Tenant-Id`**，缺失 **400**。 |
| **`DEVAULT_AUTH_SOURCE=legacy`** | 仓库当前以 **IAM JWKS/PEM 是否配置** 切换 dev-open / IAM JWT；无独立 **`DEVAULT_AUTH_SOURCE`** 开关。 |
| **`src/devault/api/deps.py`** | 仅从请求显式租户解析；**禁止**回落到 `default` 或任意「首个租户」。 |
| **租户镜像** | IAM 创建租户后同步 DeVault `tenants` 表，避免 FK 与控制台列举不一致。 |
| **Agent** | enrollment 必须显式配置；与 §9 一致。 |

---

## 11. 实现顺序建议（非向后兼容）

以下按 **合并风险** 拆分 PR，**不**承诺与旧安装、旧数据共存；旧迁移文件中与 default 自助注册相关的逻辑应 **直接改写或删除**，而非并行保留。

| 阶段 | 内容 |
|------|------|
| **A** | 加列 `is_platform_admin`、`must_change_password`（可选）；实现 CLI（§6）；**删除**注册路由与 `register_user`、`self_registration_enabled` |
| **B** | 种子与迁移：**不再**插入 default 租户；**删除** `get_default_tenant` 及调用链；改写假设 `slug=default` 的迁移 / 演示数据 |
| **C** | IAM：`login` / JWT / `Principal` / `POST /v1/tenants` 按 §5；DeVault：`deps`、JWT 解析、移除默认租户配置 |
| **D** | Compose / CI E2E / `website/docs` 按 §9；`iam-service-design` API 表更新 |

每阶段需：**审计、集成测试、PR 自检**。

---

## 12. 按优先级待办项（实现清单）

**实现状态（仓库）**：**P0–P7（本文清单）** 已落地——IAM 侧见上文；**DeVault** 已强制 **`X-DeVault-Tenant-Id`**、移除 **`DEVAULT_DEFAULT_TENANT_SLUG`**、**`iam_jwt`** 仅以 **`pk=platform`** 识别平台 JWT、**`POST /api/v1/tenants`** 支持 **`id`** 与 IAM 对齐、**`deploy/scripts/bootstrap_demo_stack.py`** + Compose **`with-console`** profile（**`demo-stack-init`** 与 **console** 同 profile；**`make demo-stack-up`** 一键含 IAM 演示平台 bootstrap）、网站文档与快速开始已更新。详见 [`iam/README.md`](../iam/README.md)、[`deploy/docker-compose.yml`](../deploy/docker-compose.yml)、[`deploy/scripts/bootstrap_demo_stack.py`](../deploy/scripts/bootstrap_demo_stack.py)。

以下按 **依赖顺序** 排列：数字越小越应先做；同优先级内可并行（不同文件）但需在合并前跑通集成。**状态**列：`[x]` 已在仓库落地，`[ ]` 未实现。**完成某项后**建议在 [`iam/docs/BACKLOG.md`](../iam/docs/BACKLOG.md) 与本文 §15 修订记录中交叉标注。

### P0 — 数据模型与约束（阻塞后续）

| 状态 | ID | 待办项 | 说明 / 涉及路径 |
|------|-----|--------|-----------------|
| [x] | P0-1 | Alembic：`users.is_platform_admin`、`users.must_change_password`（可选） | 迁移 `p4_001`；现有行默认 `false` |
| [x] | P0-2 | ORM / 模型同步 | `iam/src/devault_iam/db/models.py` |
| [x] | P0-3 | 互斥校验（应用层） | `platform_user_rules`；`POST .../members` 拒绝 `is_platform_admin` 用户；成员角色不含 `platform_admin`（`schemas/tenants.py`） |

### P1 — 独立 CLI Bootstrap

| 状态 | ID | 待办项 | 说明 |
|------|-----|--------|------|
| [x] | P1-1 | `iam/pyproject.toml` 注册 `console_scripts`（`iam-admin`） | `devault_iam.cli_admin:main` |
| [x] | P1-2 | 实现 `bootstrap create-platform-user` / `bootstrap status` | 幂等、stdin / `--password-file`、审计 `platform.bootstrap`（`cli_admin.py`） |
| [x] | P1-3 | 文档：运维在 `alembic upgrade` 之后执行 CLI | `iam/README.md`（`deploy/` 共用 compose 仍为 `alembic upgrade head`，未单独改 compose 文案） |

### P2 — 平台 JWT、`Principal`、登录（无租户上下文）

| 状态 | ID | 待办项 | 说明 |
|------|-----|--------|------|
| [x] | P2-1 | `issue_access_token` / `login_user` 分支 | `is_platform_admin` ⇒ `pk=platform`、`perm` 仅平台 keys、`tid` 不回落 |
| [x] | P2-2 | `get_current_principal` / `decode` 校验 | 平台员 **不**要求 `tid ∈ tenant_ids_for_user`；租户用户保持现状 |
| [x] | P2-3 | 移除或重写 `user_is_platform_admin` | 已改为读 `users.is_platform_admin`（`permissions.py`；不再用租户内 `platform_admin` 角色表达平台员） |
| [x] | P2-4 | `resolve_effective_tenant_id` | 平台登录无 `tid` 时不得解析到 default；租户用户禁止依赖 `slug=default` |
| [x] | P2-5 | `POST /v1/tenants` 鉴权 | 创建租户仅 `is_platform_admin` JWT（或等价 `perm`） |

### P3 — 关闭自助注册与注册代码清理

| 状态 | ID | 待办项 | 说明 |
|------|-----|--------|------|
| [x] | P3-1 | **删除** `self_registration_enabled` 及所有读取点 | `iam` settings 与路由分支 |
| [x] | P3-2 | **删除** `POST /v1/auth/register` 与 `register_user` | `auth.py`、`auth_service.py` |
| [x] | P3-3 | 测试替换 | 所有依赖注册的 `iam/tests` 改为 CLI / 管理 API |
| [x] | P3-4 | Console 移除注册路由与入口 | `config.ts`、`login`、`register` 页、i18n |
| [x] | P3-5 | OpenAPI / `console` 类型同步 | Console `openapi-typescript` 绑定控制面 schema；IAM 无并入，本项记为已核对 |

### P4 — 管理面：创建用户与成员（平台员登录后可用）

| 状态 | ID | 待办项 | 说明 |
|------|-----|--------|------|
| [x] | P4-1 | `POST /v1/platform/users`（或约定路径） | 创建非平台用户、可选 `must_change_password`；**仅** `is_platform_admin` JWT |
| [x] | P4-2 | `PATCH /v1/platform/users/{id}`（可选） | 重置密码、改 `must_change_password`；禁止修改 `is_platform_admin` 用户 |
| [x] | P4-3 | `POST/DELETE .../members` 与平台员校验 | `PATCH`/`DELETE` 对目标用户为平台员时 **400**（与 `POST` 一致） |
| [x] | P4-4 | 首次登录强制改密（若采用 `must_change_password`） | **`TokenOut.must_change_password`** + **`POST /v1/auth/change-password`**；DeVault 会话闸门 **P6** 另项 |

### P5 — 无默认租户（种子与运行时）

| 状态 | ID | 待办项 | 说明 |
|------|-----|--------|------|
| [x] | P5-1 | 迁移与种子：**不得**再 `bulk_insert` default 租户 | `p0_001` 已去掉 default 租户插入 |
| [x] | P5-2 | 删除 / 弃用 `get_default_tenant` | 已无该辅助函数 |
| [x] | P5-3 | 调整 RBAC 种子文档 | `iam/docs/BACKLOG.md`、§3 对照表已更新 |

### P6 — DeVault 控制面

| 状态 | ID | 待办项 | 说明 |
|------|-----|--------|------|
| [x] | P6-1 | `deps.py` 租户解析 | 缺 **`X-DeVault-Tenant-Id`** → **400**；已移除 **`default_tenant_slug`** 配置 |
| [x] | P6-2 | `iam_jwt.py` / `AuthContext` | 平台 JWT 仅以 **`pk=platform`** 映射为 **`allowed_tenant_ids=None`**（与 IAM / Console session 语义一致） |
| [x] | P6-3 | IAM 创建租户 → DeVault 镜像 | **`POST /api/v1/tenants`** 支持可选 **`id`**；编排脚本 **`deploy/scripts/bootstrap_demo_stack.py`** |
| [x] | P6-4 | 改写 / 删除假设 **`slug=default`** 的迁移与种子 | **`0011`** enrollment 种子改为「最早租户行」；**`0005`** 仍为历史首迁（单条种子租户；新装无 IAM 时仍有一条占位） |

### P7 — 演示栈与文档（不阻塞核心路径）

| 状态 | ID | 待办项 | 说明 |
|------|-----|--------|------|
| [x] | P7-1 | `deploy/scripts/` 或 compose init 容器 | **`bootstrap_demo_stack.py`**（IAM 登录 → 建租户 → DeVault 镜像 UUID） |
| [x] | P7-2 | `docker-compose` 与 CI E2E | **`demo-stack-init`** + **`with-console`**；**`make demo-stack-up`** 含 IAM **`IAM_DEMO_AUTO_BOOTSTRAP`** 与默认 **`DEMO_STACK_PLATFORM_*`**；无 **`with-console`** 的 **`up`** 不跑 init / console |
| [x] | P7-3 | `website/docs/user/quickstart.md`、`iac-bootstrap.md`、`tenants-and-rbac.md` | 显式租户头、无默认 slug、与 **`0011`** 说明 |
| [x] | P7-4 | `docs/iam-service-design.md` §7 API 表 | 增补 DeVault **`POST /api/v1/tenants`** 可选 **`id`** 与强制租户头说明 |

### 优先级与 §11 阶段对应关系

| 本文 §11 阶段 | 主要待办优先级 |
|---------------|----------------|
| **A** | P0、P1、P3（可与 P2 设计并行，合并前跑通集成） |
| **B** | P5 |
| **C** | P2、P4、P6 |
| **D** | P7 |

---

## 13. 安全与审计

- 所有 **bootstrap、创建用户、创建租户、成员变更** 写入 IAM `audit_logs`。  
- 平台员密钥与数据库 URL **分权**：CI 使用短期凭据。  
- 定期复核：`SELECT * FROM users WHERE is_platform_admin = true` 人数与账号归属。

---

## 14. 相关链接

- [`docs-old/iam.md`](../docs-old/iam.md) — 组织与 IAM 原则（改版参考）  
- [`docs/iam-service-design.md`](iam-service-design.md) — 独立 IAM 服务设计与 DeVault 集成  
- [`iam/docs/BACKLOG.md`](../iam/docs/BACKLOG.md) — 实现待办与优先级  
- [`docs/README.md`](README.md) — `docs/` 索引  

---

## 15. 修订记录

| 日期 | 说明 |
|------|------|
| 2026-05-11 | 初稿：无默认租户、平台员用户标志位、独立 CLI bootstrap、关闭自助注册、演示栈 API 初始化、DeVault 对齐要点。 |
| 2026-05-11 | 新增 §12「按优先级待办项（P0–P7）」及与 §11 阶段映射表；原 §12–§14 顺延为 §13–§15。 |
| 2026-05-11 | 明确**不要求向后兼容**：文首策略说明；§3、§7、§10–§11、§12（P0-4 删除、P3/P5/P6 收紧）移除迁移期 / legacy / 双轨 / 存量数据迁移表述。 |
| 2026-05-11 | **P0 / P1 已落地**：`p4_001` 迁移与 ORM 字段、`platform_user_rules`、成员 API 校验、`iam-admin` CLI、§12 实现状态说明。 |
| 2026-05-11 | §7.2、§12：待办项增加 **状态** 列，`[x]` 标记已完成（P0、P1），`[ ]` 未实现。 |
| 2026-05-11 | **P2 / P3 已落地**：平台 JWT 与 `Principal`、`resolve_effective_tenant_for_login`、删 `register` 与 `self_registration`、Console 去注册、§7.2 与 §12 勾选同步。 |
| 2026-05-11 | **P4 / P5（IAM）已落地**：`/v1/platform/users`、`/v1/auth/change-password`、`TokenOut.must_change_password`、成员 PATCH/DELETE 平台员防护；`p0_001` 不再插入 default 租户；集成测试会话夹具与 `IAM_TEST_PLATFORM_*` 说明见 `iam/README.md`。 |
| 2026-05-11 | **P6 / P7 已落地**：DeVault 强制租户头、删 `DEVAULT_DEFAULT_TENANT_SLUG`、`iam_jwt` 平台判定收紧、`TenantCreate.id`、**`0011`** 种子逻辑、`deploy/scripts/bootstrap_demo_stack.py` 与 Compose **`with-console`**（演示 bootstrap + **`demo-stack-init`**）、网站与 **`docs/iam-service-design.md`** 更新。 |
