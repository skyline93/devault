# DeVault IAM（独立服务）

本目录为 **独立可部署** 的 IAM 服务代码，与 `src/devault` **无源码依赖**。设计说明见 **[`docs/iam-service-design.md`](../docs/iam-service-design.md)**；**按优先级的实现待办**见 **[`iam/docs/BACKLOG.md`](docs/BACKLOG.md)**。

## 范围

- **包含**：人类身份、租户与成员、RBAC、控制面 API Key、`/authorize`、JWT/JWKS（设计见文档；代码逐步落地）。
- **不包含**：Agent、gRPC enrollment、备份业务对象（由 DeVault 负责）。

## 本地运行

```bash
cd iam
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
export IAM_DATABASE_URL=postgresql+psycopg://iam:iam@127.0.0.1:5432/iam
uvicorn devault_iam.api.main:app --reload --port 8100
```

健康检查：<http://127.0.0.1:8100/health>

或使用入口脚本：

```bash
devault-iam-serve
```

## 数据库迁移

```bash
cd iam
export IAM_DATABASE_URL=...
alembic upgrade head
```

若本地曾应用过已删除的占位 revision **`0001_initial`**，请先 `alembic downgrade base` 或手动清理 `alembic_version` 后再执行 `upgrade head`（当前链为 **`p0_001` → `p2_001` → `p3_001`**，以 `alembic heads` 为准）。

## Docker

在 **`iam/`** 目录下构建（上下文为当前目录）：

```bash
docker build -f Dockerfile -t devault-iam:local .
docker run --rm -p 8100:8100 -e IAM_DATABASE_URL=... devault-iam:local
```

或从**仓库根目录**使用独立 Compose（含 Postgres + Redis + 迁移）：

```bash
docker compose -f deploy/docker-compose.iam.yml up --build
```

## 环境变量

| 变量 | 说明 |
|------|------|
| `IAM_DATABASE_URL` | PostgreSQL 连接串（独立库） |
| `IAM_REDIS_URL` | Redis（限流/缓存等） |
| `IAM_JWT_ISSUER` | JWT `iss` |
| `IAM_JWT_AUDIENCE` | 默认 `devault-api` |
| `IAM_CORS_ORIGINS` | 逗号分隔的 Console origin，可为空 |
| `IAM_ENVIRONMENT` | `development`（默认）或 `production`；生产环境会强制校验 JWT 与 HTTPS issuer |
| `IAM_TEST_DATABASE_URL` | 仅测试：覆盖默认的 `postgresql+psycopg://iam:iam@127.0.0.1:5433/iam` |
| `IAM_SELF_REGISTRATION_ENABLED` | 默认 `true`；为 `false` 时除「库中无任何用户」外的自助注册返回 403 |
| `IAM_ACCESS_TOKEN_TTL_SECONDS` | 默认 `900` |
| `IAM_REFRESH_TOKEN_TTL_SECONDS` | 默认 `604800`（7 天） |
| `IAM_LOGIN_RATE_LIMIT_PER_MINUTE` | 默认 `60`（依赖 Redis；不可用时跳过限流） |
| `IAM_AUTHORIZE_RATE_LIMIT_PER_MINUTE` | 默认 `240`（`/v1/authorize`；Redis 不可用时跳过） |
| `IAM_PERMISSION_CACHE_TTL_SECONDS` | 默认 `300`（用户/API Key 权限列表缓存 TTL） |
| `IAM_API_KEY_ACCESS_TOKEN_TTL_SECONDS` | 默认 `1800`（API Key 换得的 access JWT 有效期） |
| `IAM_INTERNAL_API_TOKEN` | 可选；**非空**时 `POST /v1/authorize` 必须带 **`X-Iam-Internal`** 且值相等，否则 401（DeVault 等服务账号调用时的 **service token** 模式；生产可再配合网络策略 / 未来 mTLS） |
| `IAM_METRICS_ENABLED` | 默认 `true`；为 `false` 时 **`GET /metrics`** 返回 404 |
| `IAM_HTTP_ACCESS_LOG_ENABLED` | 默认 `true`；为 `false` 时关闭 `devault_iam.access` 访问日志 |
| `IAM_ACCESS_LOG_JSON` | 默认 `false`；为 `true` 时访问日志为单行 JSON（便于 Loki / ELK） |

### P1 HTTP 接口摘要

- `POST /v1/auth/register` · `POST /v1/auth/login` · `POST /v1/auth/refresh` · `POST /v1/auth/logout`
- `POST /v1/auth/mfa/enroll/start` · `POST /v1/auth/mfa/enroll/confirm` · `POST /v1/auth/mfa/disable`（后两者需 Bearer）
- `GET /.well-known/jwks.json`
- `GET /v1/me`（Bearer）
- `GET/POST /v1/tenants` · `GET/PATCH /v1/tenants/{id}`（Bearer + 权限见 OpenAPI）
- `GET/POST/PATCH/DELETE /v1/tenants/{tenant_id}/members/...`（Bearer）

登录/注册/刷新可带 **`X-DeVault-Tenant-Id`** 或 **`X-Tenant-Id`** 选择当前租户（须为成员）。

### P2 HTTP 接口摘要

- `GET/POST /v1/platform/api-keys`、`GET/POST /v1/tenants/{tenant_id}/api-keys`（Bearer；平台/租户管理员权限见 OpenAPI）
- `PATCH/DELETE /v1/api-keys/{id}`（Bearer）
- `POST /v1/auth/token`（公开）：`{"grant_type":"api_key","api_key":"dvk...."}` → access JWT（人机 IAM 路由仍拒绝 `api_key:` 主题的 Bearer）
- `POST /v1/authorize`（公开或受 `IAM_INTERNAL_API_TOKEN` 保护）：`subject` + `tenant_id` + `action` → `{ "allowed": bool }`

### P3 HTTP 与运维

- `GET /v1/platform/audit-logs`（Bearer + `devault.platform.admin`）：分页审计，查询参数 `limit`、`offset`、`action_prefix`
- `GET /metrics`：Prometheus 文本（`devault_iam_http_*` 系列指标；不在 OpenAPI 中展示）
- 所有响应带 **`X-Request-Id`**（可请求头传入 `X-Request-Id` 做全链路关联，≤80 字符）

### 安全与部署注意（P3）

- **CORS**：仅当设置 **`IAM_CORS_ORIGINS`**（逗号分隔）时启用 `CORSMiddleware`；未配置则浏览器直连需同源或代理。  
- **Cookie**：当前 IAM API 以 **Authorization Bearer** 为主，不依赖 Cookie 会话；若未来 BFF 使用 Cookie，需单独 SameSite/HttpOnly 策略与文档。  
- **`/authorize`**：除限流外，建议生产设置 **`IAM_INTERNAL_API_TOKEN`**，由 DeVault（或内网网关）注入 **`X-Iam-Internal`**，避免公网任意调用。
