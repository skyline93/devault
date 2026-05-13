---
sidebar_position: 3
title: 快速开始
description: 使用 Docker Compose 最短路径跑通备份与恢复
---

# 快速开始

以下步骤假设你在仓库根目录克隆了 DeVault，并已安装 Docker Compose。该路径用于 **自托管体验**；云上 SaaS 租户通常使用托管终端与控制台，无需本地 Compose。

## 1. 启动栈

仅内置 **Postgres / Redis / MinIO**（无 profile）：

```bash
cd deploy
docker compose pull && docker compose up -d
```

要启动 **IAM + api + scheduler**（及按需 **agent**、**控制台**），需启用 [Docker Compose profiles](https://docs.docker.com/compose/how-tos/profiles/)，例如与历史一键安装等价的控制面 + Agent：

```bash
cd deploy
docker compose pull && docker compose --profile with-control-plane --profile with-agent up -d
```

带官方 **Web 控制台** 与演示租户初始化（**`make demo-stack-up`** 等同启用 **with-control-plane**、**with-agent**、**with-console**）：

```bash
docker compose --profile with-control-plane --profile with-agent --profile with-console up -d --build
```

应用镜像为预构建 **`DEVAULT_IMAGE`**（默认见 `docker-compose.yml`）。`api` 启动时会执行 `alembic upgrade head`。profile 说明见 [Docker Compose 管理文档](../admin/docker-compose.md)。

**Agent 与多租户**：在控制台或 **`POST /api/v1/agent-tokens`** 为租户创建 **Agent 令牌**（明文仅创建时返回一次），将值配置为边端 **`DEVAULT_AGENT_TOKEN`**。**`make demo-stack-up`** 下 **`demo-stack-init`** 会在租户镜像成功后调用同一 HTTP API 签发演示令牌，并写入 Compose 共享卷；**`agent`** 从卷读取（亦可在 **`deploy/.env`** 中显式设置 **`DEVAULT_AGENT_TOKEN`** 覆盖）。Agent 启动后 **`Register`** 会分配或确认 **`agent_id`** 并上报主机快照；**`Heartbeat`** 仅刷新存活与版本校验。详见 [Agent 舰队](../admin/agent-fleet.md) 与 [gRPC（Agent）](../reference/grpc-services.md)。策略创建时 **必填 `bound_agent_id`**（须为已注册实例）。可在写入策略后用 **`POST /api/v1/jobs/path-precheck`**（或 Web UI 策略页的 **Run path precheck**）让 Agent 只读校验 **`paths`** 是否存在、可读，再上真实备份。

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
docker compose --profile with-control-plane --profile with-agent exec agent mkdir -p /restore/out
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
