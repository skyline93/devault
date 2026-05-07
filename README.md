# DeVault

开发者向备份平台。当前仓库已实现 **文件全量备份 / 文件恢复到指定目录**（FastAPI + Celery + PostgreSQL 元数据 + S3 兼容存储）。

- 产品愿景：[`docs/README.md`](docs/README.md)  
- 开发设计：[`docs/development-design.md`](docs/development-design.md)

## 用 Docker Compose 跑通备份与恢复

```bash
cd deploy
docker compose up --build -d
```

Worker 已将仓库内 `demo_data/` 挂载为只读 **`/data`**，并将卷 **`worker_restore`** 挂载为 **`/restore`**。允许的路径前缀为 **`/data`** 与 **`/restore`**（见 `deploy/docker-compose.yml`）。

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

在 Worker 容器内先建空目录（路径需在允许前缀下）：

```bash
docker compose exec worker mkdir -p /restore/out
```

发起恢复任务：

```bash
curl -sS -H "Authorization: Bearer changeme" -H "Content-Type: application/json" \
  -d '{"artifact_id":"<AID>","target_path":"/restore/out","confirm_overwrite_non_empty":false}' \
  http://127.0.0.1:8000/api/v1/jobs/restore
```

轮询返回的 `job_id` 至 `success` 后检查：

```bash
docker compose exec worker find /restore/out -type f -print
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

需要 PostgreSQL、Redis；存储可用 `DEVAULT_STORAGE_BACKEND=local` 或 MinIO（`s3`）。

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

export DEVAULT_DATABASE_URL=postgresql+psycopg://devault:devault@localhost:5432/devault
export DEVAULT_REDIS_URL=redis://localhost:6379/0
export DEVAULT_API_TOKEN=dev
export DEVAULT_STORAGE_BACKEND=local
export DEVAULT_LOCAL_STORAGE_ROOT=./data/storage

alembic upgrade head
uvicorn devault.api.main:app --reload --port 8000
# 另一终端
celery -A devault.worker.app worker --loglevel=INFO
```

## 测试

```bash
pytest -q
```

## 许可证

MIT（可按需修改）
