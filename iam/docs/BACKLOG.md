# IAM 实现待办清单（按优先级）

依据：

- **[`docs/iam-service-design.md`](../../docs/iam-service-design.md)** — DeVault 独立 IAM 收敛范围（人 + 控制面 API Key）与 JWT/集成约定  
- **[`docs-old/iam.md`](../../docs-old/iam.md)** — 通用 IAM 原则：职责边界、Authorize、`permission key`、缓存思路、审计分层、未来扩展

**范围说明（`iam-service-design`）**：本服务 **不包含** `docs-old/iam.md` 中的 **Service Account / Agent** 数据面；机器身份与 gRPC enrollment **留在 DeVault**。`docs-old` 中的 **Policy Engine / SSO / JIT** 列入 **低优先级或后续 Epic**，不在首版阻塞项。

**当前代码基线**：`iam/` 为独立 FastAPI 服务（Alembic 至 **`p4_001`**：在 **`p3_001`** 之上增加 ``users.is_platform_admin`` / ``must_change_password``；**`iam-admin bootstrap`** CLI，见 **[`docs/iam-tenant-lifecycle-and-bootstrap.md`](../../docs/iam-tenant-lifecycle-and-bootstrap.md)**）。成员 API **拒绝**将 ``is_platform_admin`` 用户加入租户；成员 JSON **不得**使用 ``platform_admin`` 角色（平台身份仅用标志位 + 后续 JWT 分支）。其余：人类认证、租户与成员、API Key、`/v1/authorize`、Redis 限流与权限缓存、**审计表**、**Prometheus `/metrics`**、访问日志与 **`X-Request-Id`**；细节以 OpenAPI 与测试为准。

---

## 优先级定义

| 级别 | 含义 |
|------|------|
| **P0** | 不完成则无法称为「可联调的 IAM」 |
| **P1** | MVP：Console 人类用户可登录、带租户上下文、DeVault 可验 JWT |
| **P2** | 控制面 API Key + 统一授权 + 权限缓存 |
| **P3** | 身份审计、安全与运维硬化 |
| **P4** | 体验与扩展（邀请、联邦登录、策略引擎等） |
| **P5** | **跨仓库**：DeVault / Console 迁移与双写（在 `src/devault`、`console/` 执行，本清单仅列依赖与验收点） |

---

## P0 — 基础能力（数据 + 会话基础设施）

1. **ORM 与首版迁移（Alembic）**  
   - [x] 按设计落地表：`users`（含 `name`、`status`、`mfa_enabled`、`totp_*`、`updated_at` 等与 `iam-service-design` §5.1 一致）  
   - [x] `sessions`（refresh 吊销、可选与 Redis 黑名单联动）— 对齐 `docs-old/iam.md` §sessions（表结构已就绪；Redis 黑名单为后续）  
   - [x] `tenants`、`tenant_members`（代理主键 `id`、`role_id` FK）  
   - [x] `roles`（`tenant_id` nullable 平台角色）、`permissions`、`role_permissions`（含 PG14 部分唯一索引）  
   - [x] **种子数据**：6 条 `permissions`、`tenant_admin` / `operator` / `auditor` / `platform_admin` 及 `role_permissions`；**不**再插入占位租户（首迁 `p0_001` 仅 schema + RBAC 模板）  
   - [x] 占位 revision `0001_initial` 已移除，基线为 **`p0_001`**（`alembic/versions/p0_001_schema_and_seed.py`）  

2. **数据库会话与仓库层**  
   - [x] `SessionLocal` / `get_db` FastAPI 依赖（`devault_iam.db.session`）  
   - [x] 基础 Repository：`repositories/rbac.py`；`services/readiness.py`  

3. **配置扩展**  
   - [x] `IAM_JWT_PRIVATE_KEY` / `IAM_JWT_PUBLIC_KEY` / `IAM_JWT_PRIVATE_KEY_FILE` / `IAM_JWT_PUBLIC_KEY_FILE`、`IAM_JWT_KEY_ID`  
   - [x] `IAM_ENVIRONMENT=production` 时启动校验（`lifespan` → `assert_production_config`）：HTTPS issuer、JWT 公私钥必填  

4. **测试与 CI**  
   - [x] `iam/tests`：生产配置单测 + 连接 Postgres 的 schema/ready 集成测试（`IAM_TEST_DATABASE_URL`）  
   - [x] 根仓库 **`.github/workflows/ci.yml`** 增加 **`iam-test`** job（Postgres service + alembic + pytest）  

**验收**：`alembic upgrade head` 后库内有完整 RBAC 表 + 种子；单元测试可连真实 Postgres 或等价容器。

---

## P1 — 身份 + 租户 + RBAC + JWT/JWKS（人类用户 MVP）

5. **密码与账户**  
   - [x] Argon2id 哈希与校验（`security/passwords.py`，最少 12 位，与 DeVault 对齐）  
   - [x] ~~`POST /v1/auth/register`~~（**已删除**；首用户由 **`iam-admin bootstrap`** 创建，见 `docs/iam-tenant-lifecycle-and-bootstrap.md`）  
   - [x] `POST /v1/auth/login` → **access JWT** + **refresh**（`sessions.refresh_token_hash`）  
   - [x] `POST /v1/auth/refresh`、`POST /v1/auth/logout`（吊销 refresh；refresh 旋转）  
   - [x] 登录限流（Redis `INCR`，不可用时 fail-open；`IAM_LOGIN_RATE_LIMIT_PER_MINUTE`）  

6. **MFA（`docs-old` Session / MFA 模块）**  
   - [x] TOTP：`POST /v1/auth/mfa/enroll/start`、`/enroll/confirm`、`/disable`；JWT `mfa` claim  
   - [x] 登录：若已启用 MFA 则必须在同一请求提供 `mfa_code`（否则 `403` + `mfa_required`）  

7. **租户与成员 API**  
   - [x] `GET/POST /v1/tenants`、`GET/PATCH /v1/tenants/{id}`（平台建租户；读需 `devault.console.read`；改需 `devault.console.admin` 或平台）  
   - [x] `GET/POST/PATCH/DELETE /v1/tenants/{tenant_id}/members`（`devault.console.admin` 管理成员）  
   - [x] 请求头 **`X-DeVault-Tenant-Id`** / **`X-Tenant-Id`** 参与 login/refresh 的 `tid` 解析（与 `resolve_effective_tenant_id` 一致）  

8. **JWT 签发与 JWKS**（`iam-service-design` §8 + `docs-old` Gateway 验签思路）  
   - [x] Access JWT：`sub`、`iss`、`aud`、`iat`、`exp`、`jti`、`tid`、`tids`、`perm`、`pk`、`mfa`（RS256 + `kid`）  
   - [x] `GET /.well-known/jwks.json`（`RSAAlgorithm.to_jwk`）  
   - [x] 登录/注册/刷新响应 **`TokenOut.permissions`**  

9. **依赖保护路由**  
   - [x] `get_current_principal`（Bearer access JWT；权限与租户集合同步自 DB）  
   - [x] 公开路径：`/health`、`/docs`、`/redoc`、`/openapi.json`、`/.well-known/jwks.json`、`/v1/auth/*`（MFA enroll 需 Bearer）、`/v1/ready`、`/v1/readyz`、`/v1/meta`  

**验收**：人类用户完成注册/登录→获得 JWT→JWKS 可拉取→payload 含 `tid` 与 `perm`；成员变更后新登录权限正确。

---

## P2 — 控制面 API Key + Authorize + 权限缓存

10. **API Key 模块**（`iam-service-design` §5.4，`docs-old` §api_keys / api_key_scopes）  
    - [x] `api_keys` + `api_key_scopes`；`key_prefix` + `key_hash`；创建时 **一次性明文** `secret` 返回（`ApiKeyCreatedOut`）  
    - [x] `GET/POST /v1/tenants/{tenant_id}/api-keys`；`GET/POST /v1/platform/api-keys`（权限：`devault.console.admin` / `devault.platform.admin`）  
    - [x] `PATCH /v1/api-keys/{id}`（启用/禁用）、`DELETE /v1/api-keys/{id}`  

11. **API Key → JWT**  
    - [x] `POST /v1/auth/token`，`grant_type=api_key`：校验 secret → 签发短期 JWT（`sub=api_key:{uuid}`，`pk=api_key`，`perm` 来自 scopes）  

12. **`POST /v1/authorize`**（`docs-old` §十一、十二）  
    - [x] 请求体：`subject`、`tenant_id`、`action`、`resource`（预留；首版不参与判定）  
    - [x] 响应：`{ "allowed": true/false }`；用户侧使用 **租户内** RBAC（`permissions_for_user_in_tenant`），与 access JWT 中 `perm` 的「多租户 union」语义刻意区分  
    - [x] 可选：`IAM_INTERNAL_API_TOKEN` 非空时要求请求头 **`X-Iam-Internal`** 与之相等（否则 401）  

13. **Redis 权限缓存**（`docs-old` §十三）  
    - [x] 键：`iam:perm:user:{tenant_id}:{user_id}`、`iam:perm:api_key:{api_key_id}`（TTL `IAM_PERMISSION_CACHE_TTL_SECONDS`）  
    - [x] 失效：成员增删改、`PATCH/DELETE` API Key 后主动删缓存（`invalidate_user_tenant` / `invalidate_api_key`）；Redis 不可用时读缓存失败 **fail-open** 回源 DB  

**验收**：API Key 可换 JWT；`/authorize` 与缓存有集成测试（`iam/tests/test_p2_api_key_authorize.py`）。

---

## P3 — 身份审计、安全与可观测性

14. **身份域审计**（`docs-old` §六/十八：IAM 侧事件；业务审计仍在 DeVault）  
    - [x] `audit_logs` 表（`p3_001`）+ `record_audit_event`（独立会话写入，失败不影响主请求）  
    - [x] 覆盖：`auth.register` / `auth.login` / `auth.refresh` / `auth.api_key_token`；`mfa.*`；`tenant.member.*`；`api_key.*`（成功与关键失败；不含业务资源 `POST` 上报）  
    - [x] **`GET /v1/platform/audit-logs`**（`devault.platform.admin`；`limit`/`offset`/`action_prefix`）  

15. **安全硬化**  
    - [x] CORS、鉴权形态与 **`/authorize` 服务令牌**（`IAM_INTERNAL_API_TOKEN` + `X-Iam-Internal`）在 **[`iam/README.md`](../README.md)**「安全与部署注意」中说明；当前人机鉴权为 **Bearer JWT**（非 Cookie 会话）  
    - [x] 登录/API Key 换票/authorize 限流与密码策略（P1 已具备）；refresh 旋转（P1）；**mTLS** 列为后续运维加固（本阶段以网络隔离 + 内部令牌为主）  

16. **运维**  
    - [x] **`GET /metrics`**（`prometheus_client`；`IAM_METRICS_ENABLED=false` 时返回 404）  
    - [x] 访问日志（`devault_iam.access`）+ 请求 **`X-Request-Id`**（可客户端传入，长度 ≤80）  
    - [x] **`IAM_ACCESS_LOG_JSON=true`** 时单行 JSON 访问日志；OpenAPI 以 **`/v1`…** 前缀版本化（初版满足）  

**验收**：平台管理员可拉审计列表；Prometheus 可抓取 `/metrics`；响应带可关联的 `X-Request-Id`（见 `iam/tests/test_p3_audit_metrics.py`）。

---

## P4 — 产品化与 `docs-old` 中的「未来能力」（按需排期）

17. **租户邀请**（若与现 DeVault `tenant_invitations` 对齐）  
    - [ ] 邮件邀请 token、接受流程、角色预置  

18. **联邦登录 / SSO**（`docs-old` §二十 · SSO）  
    - [ ] OIDC 代码流或 broker；与纯密码账户绑定策略  

19. **Policy Engine / 审批 / JIT**（`docs-old` §二十）  
    - [ ] 明确为 **独立 Epic**：与 Authorize 扩展点（`resource`）衔接设计，**不阻塞** P1–P2  

20. **租户 → DeVault 镜像同步**（`iam-service-design` §9）  
    - [ ] Webhook / 消息队列 / 同步 API：IAM 为权威源，DeVault `tenants` 镜像；**实现可能在 P5 与 DeVault 协同**  

---

## P5 — DeVault / Console 侧（依赖 P1+，本仓库非 `iam/` 独占）

21. **DeVault**（首版灰度已实现；见 `src/devault/security/iam_jwt.py`、`tests/test_iam_jwt_auth.py`）  
    - [x] **`DEVAULT_IAM_JWKS_URL`**（PyJWKClient）或 **`DEVAULT_IAM_JWT_PUBLIC_KEY_PEM`**（单钥免 HTTP）+ **`DEVAULT_IAM_JWT_ISSUER`** / **`DEVAULT_IAM_JWT_AUDIENCE`**（与 IAM 的 `iss`/`aud` 对齐）  
    - [x] **`DEVAULT_AUTH_SOURCE`**：`legacy`（默认）| `iam`（启用 IAM access JWT 校验；仍保留 OIDC、Agent Redis session、**`control_plane_api_keys`** 与 **`DEVAULT_API_TOKEN`** 等既有路径，便于双跑）  
    - [x] IAM JWT → **`AuthContext`**；**`GET /api/v1/auth/session`** 对 **`iam:user:`** 主体合成 **`AuthSessionOut`**（按 JWT `tids` 与 DeVault `tenants` 表 JOIN 展示租户行；无 `console_users` 行）  
    - [ ] **最终**移除 `console_users` / `tenant_memberships` / `control_plane_api_key` 解析（需数据迁移与租户镜像完成后）  
    - [ ] 租户镜像消费（若 §9 采用事件同步）  

22. **Console**  
    - [x] **`UMI_APP_IAM_PREFIX`**（如 `/iam-api`）时：**登录 / 注册 / IAM 侧 MFA 第二步** 请求独立 IAM；业务 **`/api/*`** 仍为 DeVault + **`Authorization`**（IAM access JWT）+ **`X-DeVault-Tenant-Id`**（见 `console/config/config.ts` 代理与 `src/pages/user/login`）  
    - [ ] Console 内 **API Key 生命周期管理** 全面切到 IAM（当前仍可用集成页的 DeVault 静态 Token / 或由运维使用 IAM OpenAPI）  

**验收（首版）**：`DEVAULT_AUTH_SOURCE=iam` 且 JWKS/公钥与 iss/aud 配置正确时，Console 经 IAM 登录后 **`GET /api/v1/auth/session`** 返回与 IAM 权限一致的会话对象；`legacy` 行为不变。

---

## 建议实施顺序（一页执行版）

1. **P0** 表结构 + 种子 + DB 会话 + pytest 骨架  
2. **P1** login → JWT → JWKS → tenants/members 最小闭环  
3. **P2** api_keys + token grant + authorize + Redis 缓存  
4. **P3** audit_logs + metrics + 安全加固  
5. **P4** 按产品需要选做（邀请、OIDC、Policy）  
6. **P5** 与 DeVault/Console 并行准备接口契约（OpenAPI 共享或生成客户端）  

---

## 文档维护

- 完成大块功能后：更新 **[`docs/iam-service-design.md`](../../docs/iam-service-design.md)** 的 **§12 实现状态** 表  
- 若调整权限 key 命名：同步 **[`website/docs/admin/tenants-and-rbac.md`](../../website/docs/admin/tenants-and-rbac.md)** 或 DeVault HTTP 文档（迁移期）
