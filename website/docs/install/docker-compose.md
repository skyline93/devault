---
sidebar_position: 2
title: Docker Compose
description: 本地与演示环境的服务角色与启动方式
---

# Docker Compose

仓库在 `deploy/docker-compose.yml` 提供一体化栈，便于快速验证备份/恢复闭环。若在 **Kubernetes** 上安装，请使用 [Kubernetes（Helm）](./kubernetes-helm.md)（`deploy/helm/devault`）。

## 启动

```bash
cd deploy
docker compose up --build -d
```

## 可选：多实例 `api`（gRPC 负载均衡）

控制面 **`api` 水平扩展**（Envoy、Compose `--scale`、调度器单副本约束）见 [gRPC 与 API 多实例部署](./grpc-multi-instance.md)。仓库提供 **`deploy/docker-compose.grpc-ha-example.yml`** 叠加示例（避免多副本与宿主机端口冲突）。

## 可选：Prometheus 与 Alertmanager

核心栈不含 Prometheus。需要本地抓取 **`/metrics`** 并走 **Alertmanager 告警路由** 时，在 `deploy/` 下叠加（含 **Prometheus、Alertmanager、演示 Webhook 接收端 `alertdump`**）：

```bash
docker compose -f docker-compose.yml -f docker-compose.prometheus.yml up -d
```

（自仓库根目录请将 `-f` 指向 `deploy/docker-compose.yml` 与 `deploy/docker-compose.prometheus.yml`。）

- Prometheus UI：[http://127.0.0.1:9090](http://127.0.0.1:9090)
- Alertmanager UI：[http://127.0.0.1:9093](http://127.0.0.1:9093)
- 查看演示 Webhook 收到的告警负载：`docker compose -f docker-compose.yml -f docker-compose.prometheus.yml logs -f alertdump`

生产接收器请编辑 `deploy/alertmanager.yml`，详见 [可观测性](./observability.md)。

## 服务角色

| 服务 | 说明 |
|------|------|
| **postgres** | 控制面元数据库；健康检查通过后再启动依赖方；备份与 PITR 规划见 [控制面元数据库备份与灾难恢复](./control-plane-database-dr.md) |
| **redis** | Redis |
| **minio** | S3 兼容对象存储 |
| **minio-init** | **一次性**任务：使用 `mc mb` 创建桶；应用运行时**不**调用 `CreateBucket`，便于 IAM 最小化 |
| **api** | 控制面：HTTP +（默认开启的）gRPC；启动命令内含 `alembic upgrade head` 与 `uvicorn`；默认配置 **`DEVAULT_GRPC_REGISTRATION_SECRET`** 以支持 Agent **Register** 引导 |
| **scheduler** | 仅负责按 Cron **创建任务**；**不**执行 `alembic` |
| **agent** | 边缘 Agent：`DEVAULT_GRPC_TARGET=api:50051`；**默认不设置** **`DEVAULT_API_TOKEN`**，启动时用 **`DEVAULT_GRPC_REGISTRATION_SECRET`**（与 **api** 相同）调 **Register** 获取内存中的 Bearer。挂载 `demo_data` → `/data`，命名卷 → `/restore` |

### Register 引导（默认开发行为）

为便于在本地验证 **Register** 与 **简易 UI → Agents** 页中的 **Registered** 时间，默认 Compose 在 **api** 与 **agent** 上配置相同的 **`DEVAULT_GRPC_REGISTRATION_SECRET`**（可用环境变量覆盖，需两端一致）。**Register** 成功后 Agent 使用 **Redis 签发的每实例 Bearer**（非共享 **`DEVAULT_API_TOKEN`**）。HTTP Basic / 本机 CLI 仍使用控制面的 **`DEVAULT_API_TOKEN`**（默认 `changeme`）。

若希望 Agent **不经 Register**、固定使用环境变量中的 token，在 **agent** 服务上显式设置 **`DEVAULT_API_TOKEN`** 即可（与 [配置参考](./configuration.md) 中 gRPC 说明一致）。

**Prometheus** 已拆到独立文件 **`docker-compose.prometheus.yml`**（见上一节），不再随默认 `up` 启动。

### Artifact 加密（可选验证）

Compose 里的 **agent** 默认注入 **`DEVAULT_ARTIFACT_ENCRYPTION_KEY`**（固定开发用 Base64，**非机密**，仅便于本地打开 **`encrypt_artifacts`** 策略时不报错）。生产或共享环境请用 **`openssl rand -base64 32`** 生成并通过环境变量覆盖；密钥只在 **Agent** 侧需要，含义与格式见 [Artifact 静态加密](../security/artifact-encryption.md)。

## 构建说明

- 镜像在 `deploy/Dockerfile` 中通过 `pip install -e .` 安装本仓库
- 构建上下文为仓库根目录；`.dockerignore` 用于缩小上下文

## gRPC TLS 与网关

若需 TLS 终结、Envoy 等叠加文件，可使用仓库提供的 `docker-compose.grpc-tls.yml` 等叠加方式（见 [TLS 与网关](../security/tls-and-gateway.md)）。可与 `docker-compose.prometheus.yml` 同时传入多个 `-f`。
