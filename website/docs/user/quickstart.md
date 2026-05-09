---
sidebar_position: 3
title: 快速开始
description: 使用 Docker Compose 最短路径跑通备份与恢复
---

# 快速开始

以下步骤假设你在仓库根目录克隆了 DeVault，并已安装 Docker Compose。该路径用于 **自托管体验**；云上 SaaS 租户通常使用托管终端与控制台，无需本地 Compose。

## 1. 启动栈

```bash
cd deploy
docker compose up --build -d
```

Compose 会拉起 PostgreSQL、Redis、MinIO、一次性 **minio-init** 建桶、**api**（含 HTTP 与 gRPC）、**scheduler**、**agent** 等。`api` 启动时会执行 `alembic upgrade head`。

默认将 `demo_data/` 挂载到 agent 容器的只读 **`/data`**，恢复卷挂载为 **`/restore`**。

## 2. 发起一次备份

```bash
export DEVAULT_API_BASE_URL=http://127.0.0.1:8000
export DEVAULT_API_TOKEN=changeme

curl -sS -H "Authorization: Bearer changeme" -H "Content-Type: application/json" \
  -d '{"plugin":"file","config":{"version":1,"paths":["/data/sample"],"excludes":[]}}' \
  http://127.0.0.1:8000/api/v1/jobs/backup
```

记下返回 JSON 中的 `job_id`，轮询直到 `status` 为 `success`：

```bash
curl -sS -H "Authorization: Bearer changeme" \
  http://127.0.0.1:8000/api/v1/jobs/<job_id>
```

## 3. 列出 artifact 并恢复

```bash
curl -sS -H "Authorization: Bearer changeme" http://127.0.0.1:8000/api/v1/artifacts
```

在 agent 容器内准备空目录（路径须在允许前缀下，如 `/restore`）：

```bash
docker compose exec agent mkdir -p /restore/out
```

发起恢复：

```bash
curl -sS -H "Authorization: Bearer changeme" -H "Content-Type: application/json" \
  -d '{"artifact_id":"<AID>","target_path":"/restore/out","confirm_overwrite_non_empty":false}' \
  http://127.0.0.1:8000/api/v1/jobs/restore
```

轮询恢复任务至成功后检查文件。

## 4. 常用入口

| 地址 | 说明 |
|------|------|
| `http://127.0.0.1:8000/docs` | OpenAPI（Swagger） |
| `http://127.0.0.1:8000/ui/jobs` | Web 控制台（Basic 密码为 `DEVAULT_API_TOKEN`） |
| `http://127.0.0.1:8000/metrics` | Prometheus 指标 |

更多环境变量与生产拓扑见 [Docker Compose](../admin/docker-compose.md) 与 [配置参考](../admin/configuration.md)。
