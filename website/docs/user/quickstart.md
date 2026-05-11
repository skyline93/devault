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
docker compose pull && docker compose up -d
```

Compose 会拉起 PostgreSQL、Redis、MinIO、一次性 **minio-init** 建桶、**api**（含 HTTP 与 gRPC）、**scheduler**、**agent** 等；应用镜像为预构建 **`DEVAULT_IMAGE`**（默认见 `docker-compose.yml`）。`api` 启动时会执行 `alembic upgrade head`。

**Agent 与多租户**：`Register` 前必须在控制面为 **`agent_id`** 配置 **`agent_enrollments`**（REST **`PUT /api/v1/agents/{agent_id}/enrollment`**）。演示栈中 **agent** 使用固定 **`DEVAULT_AGENT_ID`**，迁移 **`0011`** 会将其绑定到 **当前库中最早创建的一条租户**（开箱 Compose 下通常为迁移 **`0005`** 种子租户）。自建环境见 [Agent 舰队](../admin/agent-fleet.md)。**Heartbeat** 默认上报主机快照与可选 **`DEVAULT_ALLOWED_PATH_PREFIXES`**（逗号分隔路径前缀），供 **`GET /api/v1/tenant-agents`** 与租户级策略路径校验使用；详见 [gRPC（Agent）](../reference/grpc-services.md）。可在写入策略后用 **`POST /api/v1/jobs/path-precheck`**（或 Web UI 策略页的 **Run path precheck**）让 Agent 只读校验 **`paths`** 是否存在、可读，再上真实备份。

**REST 租户头**：除 **`GET/POST /api/v1/tenants`** 等少数路由外，业务 API 必须带 **`X-DeVault-Tenant-Id: <uuid>`**（可先 **`GET /api/v1/tenants`** 列举可用 UUID；演示栈种子租户 id 见迁移 **`0005`**）。

默认将 `deploy/demo_data/` 挂载到 agent 容器的只读 **`/data`**，恢复卷挂载为 **`/restore`**。

## 2. 解析租户 UUID（演示栈）

```bash
export DEVAULT_API_BASE_URL=http://127.0.0.1:8000
export DEVAULT_API_TOKEN=changeme
export TENANT_ID=$(curl -sS -H "Authorization: Bearer ${DEVAULT_API_TOKEN}" \
  "${DEVAULT_API_BASE_URL}/api/v1/tenants" | python3 -c "import json,sys; print(json.load(sys.stdin)[0]['id'])")
echo "$TENANT_ID"
```

## 3. 发起一次备份

```bash
curl -sS -H "Authorization: Bearer ${DEVAULT_API_TOKEN}" \
  -H "X-DeVault-Tenant-Id: ${TENANT_ID}" \
  -H "Content-Type: application/json" \
  -d '{"plugin":"file","config":{"version":1,"paths":["/data/sample"],"excludes":[]}}' \
  "${DEVAULT_API_BASE_URL}/api/v1/jobs/backup"
```

记下返回 JSON 中的 `job_id`，轮询直到 `status` 为 `success`：

```bash
curl -sS -H "Authorization: Bearer ${DEVAULT_API_TOKEN}" \
  -H "X-DeVault-Tenant-Id: ${TENANT_ID}" \
  "${DEVAULT_API_BASE_URL}/api/v1/jobs/<job_id>"
```

## 4. 列出 artifact 并恢复

```bash
curl -sS -H "Authorization: Bearer ${DEVAULT_API_TOKEN}" \
  -H "X-DeVault-Tenant-Id: ${TENANT_ID}" \
  "${DEVAULT_API_BASE_URL}/api/v1/artifacts"
```

在 agent 容器内准备空目录（路径须在允许前缀下，如 `/restore`）：

```bash
docker compose exec agent mkdir -p /restore/out
```

发起恢复：

```bash
curl -sS -H "Authorization: Bearer ${DEVAULT_API_TOKEN}" \
  -H "X-DeVault-Tenant-Id: ${TENANT_ID}" \
  -H "Content-Type: application/json" \
  -d '{"artifact_id":"<AID>","target_path":"/restore/out","confirm_overwrite_non_empty":false}' \
  "${DEVAULT_API_BASE_URL}/api/v1/jobs/restore"
```

轮询恢复任务至成功后检查文件。

## 5. 常用入口

| 地址 | 说明 |
|------|------|
| `http://127.0.0.1:8000/docs` | OpenAPI（Swagger） |
| `http://localhost:8010`（`console/` **`npm run dev`**） | Ant Design Pro 控制台（Bearer，见 [Web 控制台](./web-console.md)） |
| `http://127.0.0.1:8000/metrics` | Prometheus 指标 |

多 Agent 时可为策略绑定 **单台 Agent** 或 **Agent 池**（控制 **LeaseJobs** 谁可领该策略作业），见 [Agent 池](../admin/agent-pools.md)。

更多环境变量与生产拓扑见 [Docker Compose](../admin/docker-compose.md) 与 [配置参考](../admin/configuration.md)。
