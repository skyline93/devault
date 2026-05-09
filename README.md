# DeVault

开发者向备份平台：当前实现 **控制面（HTTP API + gRPC + Postgres/Redis）** 与 **边缘 Agent（仅 gRPC + 对象存储数据面）** 分离，采用 **Pull 模型**、可经网关扩展的 **gRPC**，以及统一的 **S3 兼容存储** 数据面。能力包括 **文件全量备份/恢复**、**策略与 Cron 定时**、**任务取消/重试**、**同策略并发锁**、**Prometheus 指标**、**简易 Web UI**。

## 文档

完整说明见 **Docusaurus 文档站**（源码在 `website/`，与 `docs-old/` 归档设计稿分离）。**控制面 ↔ Agent 兼容矩阵**（机器可读）见仓库根 **`docs/compatibility.json`**，发版清单见 **`docs/RELEASE.md`**。

- **本地预览**：`cd website && npm ci && npm start`，浏览器打开 <http://localhost:3000>  
- **在线站点**：部署后将生产 URL 写入 `website/docusaurus.config.ts` 的 `url` / `baseUrl` 并发布静态资源（见 `website/README.md`）

### 迁移数据库

首次启动或拉取含新迁移的版本后：

```bash
alembic upgrade head
```

Docker Compose 中 **仅 api** 在启动时执行 `alembic upgrade head`（**scheduler** 不再执行迁移，避免与 api 并发撞库）。

### API、Agent 与界面速览

| 路径 | 说明 |
|------|------|
| `http://127.0.0.1:8000/docs` | Swagger |
| `http://127.0.0.1:50051` | **Agent gRPC**（与 HTTP 同进程，由 `DEVAULT_GRPC_LISTEN` 开启；生产可经网关反代） |
| `http://127.0.0.1:8000/version` | 控制面版本（JSON：`version`、`api`、`grpc_proto_package`、可选 `git_sha`） |
| `http://127.0.0.1:8000/metrics` | Prometheus 指标 |
| `http://127.0.0.1:8000/ui/jobs` | 简易 UI：策略/调度 CRUD、列表内「立即备份」「恢复」、任务取消/重试（Basic 密码为 `DEVAULT_API_TOKEN`） |
| `/api/v1/policies`、`/api/v1/schedules` | 策略与 Cron 定时 CRUD |

定时任务由 **`scheduler` 服务**（`devault-scheduler`）只负责**创建待处理任务**；**`agent` 服务**通过 gRPC **拉取租约**并执行备份/恢复，经预签名 URL 与 **MinIO（S3）** 直传。控制面 `DEVAULT_STORAGE_BACKEND` 需为 **`s3`** 才能生成预签名。

### gRPC TLS、Envoy 网关与审计（阶段 A）

- 说明与操作步骤见文档站：[TLS 与网关](website/docs/security/tls-and-gateway.md)（构建后路径为 `/docs/security/tls-and-gateway`）。  
- **Envoy TLS 终结示例**（Agent → `50052` TLS → 内网 `api:50051` 明文）：先执行 `bash scripts/gen_grpc_dev_tls.sh`，再  
  `docker compose -f deploy/docker-compose.yml -f deploy/docker-compose.grpc-tls.yml up --build`。

### S3 大对象与恢复流式（阶段 B）

- 见文档站：[大对象与恢复](website/docs/storage/large-objects.md)、[存储调优](website/docs/storage/tuning.md)。  
- 相关环境变量：`DEVAULT_S3_MULTIPART_THRESHOLD_BYTES`、`DEVAULT_S3_MULTIPART_PART_SIZE_BYTES`。

### 对象存储桶（企业约定）

- **应用不会在运行时创建 S3/MinIO 桶**（不提供 `CreateBucket`），便于 IAM 最小权限与合规审计。
- **桶须事先存在**：生产环境由 **Terraform / 云控制台 / 运维脚本** 创建与 `DEVAULT_S3_BUCKET` 同名的桶。
- **Docker Compose** 通过一次性服务 **`minio-init`**（`mc mb --ignore-existing`）在 MinIO 就绪后建桶；**`api` / `agent`** 依赖其 **成功退出** 后再启动，避免 Agent 首次 PUT 时桶不存在。

## 用 Docker Compose 跑通备份与恢复

```bash
cd deploy
docker compose up --build -d
```

可选：在同一目录叠加 **Prometheus**（抓取 `api:8000/metrics`）时执行  
`docker compose -f docker-compose.yml -f docker-compose.prometheus.yml up -d`（或自仓库根目录为两个 `-f deploy/...` 路径）。

### Docker 构建（依赖只看 pyproject.toml）

- 镜像内通过 **`pip install -e .`** 安装。  
- **BuildKit pip 缓存**：`deploy/Dockerfile` 使用 `RUN --mount=type=cache,target=/root/.cache/pip`。  
- 仓库根目录 **`.dockerignore`** 会减小构建上下文（如忽略 `.venv`、`.git`）。

**agent** 将仓库内 `demo_data/` 挂载为只读 **`/data`**，卷 **`agent_restore`** 挂载为 **`/restore`**。允许的路径前缀为 **`/data`** 与 **`/restore`**（见 `deploy/docker-compose.yml`）。

### 1）发起备份

```bash
export DEVAULT_API_BASE_URL=http://127.0.0.1:8000
export DEVAULT_API_TOKEN=changeme

curl -sS -H "Authorization: Bearer changeme" -H "Content-Type: application/json" \
  -d '{"plugin":"file","config":{"version":1,"paths":["/data/sample"],"excludes":[]}}' \
  http://127.0.0.1:8000/api/v1/jobs/backup
```

记下返回的 `job_id`，轮询直到 `status` 为 `success`：

```bash
curl -sS -H "Authorization: Bearer changeme" http://127.0.0.1:8000/api/v1/jobs/<job_id>
```

### 2）列出 artifact

```bash
curl -sS -H "Authorization: Bearer changeme" http://127.0.0.1:8000/api/v1/artifacts
```

复制某个 `artifact` 的 `id`。

### 3）恢复到空目录

在 **agent** 容器内先建空目录（路径需在允许前缀下）：

```bash
docker compose exec agent mkdir -p /restore/out
```

发起恢复任务：

```bash
curl -sS -H "Authorization: Bearer changeme" -H "Content-Type: application/json" \
  -d '{"artifact_id":"<AID>","target_path":"/restore/out","confirm_overwrite_non_empty":false}' \
  http://127.0.0.1:8000/api/v1/jobs/restore
```

轮询返回的 `job_id` 至 `success` 后检查：

```bash
docker compose exec agent find /restore/out -type f -print
```

应能看到解压后的 `sources/0/...` 目录树。

## CLI（可选）

安装本仓库后：

```bash
pip install -e .
export DEVAULT_API_BASE_URL=http://127.0.0.1:8000
export DEVAULT_API_TOKEN=changeme

devault file backup /data/sample
devault job wait <job_id>
devault artifact list
devault file restore <artifact_id> --to /restore/out2 --force
```

`--force` 对应 API 的 `confirm_overwrite_non_empty=true`（目标非空时仍允许恢复）。

## 本地开发

控制面需要 PostgreSQL、Redis；**对象存储需 S3 兼容**（与 Agent 预签名一致）。本地可同时跑 **API（含 gRPC）** 与 **Agent**：

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

export DEVAULT_DATABASE_URL=postgresql+psycopg://devault:devault@localhost:5432/devault
export DEVAULT_REDIS_URL=redis://localhost:6379/0
export DEVAULT_API_TOKEN=dev
export DEVAULT_STORAGE_BACKEND=s3
export DEVAULT_S3_ENDPOINT=http://127.0.0.1:9000
export DEVAULT_S3_ACCESS_KEY=minioadmin
export DEVAULT_S3_SECRET_KEY=minioadmin
export DEVAULT_S3_BUCKET=devault
export DEVAULT_S3_USE_SSL=false
export DEVAULT_GRPC_LISTEN=0.0.0.0:50051

alembic upgrade head
uvicorn devault.api.main:app --reload --port 8000

# 另一终端（边缘 Agent：只连 gRPC + S3，勿配置数据库）
export DEVAULT_API_TOKEN=dev
export DEVAULT_GRPC_TARGET=127.0.0.1:50051
export DEVAULT_ALLOWED_PATH_PREFIXES=/data,/restore
devault-agent
```

修改 `proto/agent.proto`（含 `Register` 等 RPC）后，在项目根目录执行 **`bash scripts/gen_proto.sh`**（需已安装 `grpcio-tools`），并检查 `agent_pb2_grpc.py` 中的 **相对导入**（`from . import agent_pb2`）。

仅跑插件单元测试时仍可使用 `DEVAULT_STORAGE_BACKEND=local`，该路径不经过 Agent 预签名流水线。

## 测试

```bash
pytest -q
```

## 许可证

MIT（可按需修改）
