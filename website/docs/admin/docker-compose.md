---
sidebar_position: 5
title: Docker Compose
description: 本地与演示环境的服务角色与启动方式
---

# Docker Compose

仓库在 `deploy/docker-compose.yml` 提供一体化栈。Kubernetes 见 [Kubernetes（Helm）](./kubernetes-helm.md)（`deploy/helm/devault`）。

## 启动与 Profiles

无 profile 时仅启动 **内置数据面**：**postgres**、**redis**、**minio**、**minio-init**。

| Profile | 服务 |
|---------|------|
| **with-control-plane** | **iam**、**api**、**scheduler** |
| **with-agent** | **agent**（依赖 **api**）；与 **with-console** 任一启用时都会跑 **demo-stack-init**（IAM→DeVault 租户镜像；启用 **with-agent** 时 init 还会 **`GET`/`POST /api/v1/agent-tokens`** 并把明文写入 **`demo_stack_secrets`** 卷供 agent 读取） |
| **with-console** | **demo-stack-init**、**console**（需与 **with-control-plane** 同开） |
| **with-grpc-tls** | **grpc-gateway**（Envoy；需 **with-control-plane**；Agent TLS 叠加 **`compose.include/grpc-tls-agent.yml`** 或 **`-f docker-compose.grpc-tls.yml`**） |
| **with-monitoring** | **alertdump**、**alertmanager**、**prometheus**（需 **with-control-plane**） |

常用：

```bash
cd deploy
# 仅数据面
docker compose pull && docker compose up -d

# 控制面 + Agent（无 UI）
docker compose pull && docker compose --profile with-control-plane --profile with-agent up -d
```

远程 **`install.sh`** 默认设置 **`COMPOSE_PROFILES=with-control-plane,with-agent`**（可用 **`DEVAULT_COMPOSE_PROFILES`** 覆盖）。

## 控制台 + IAM（本地手测，接近生产链路）

仓库根目录 **`make demo-stack-up`**（或 `cd deploy` 后 **`DEVAULT_IMAGE=devault:local`** 并 **`docker compose --profile with-control-plane --profile with-agent --profile with-console up -d --build`**）：构建当前代码中的控制面镜像与 **console** 镜像，并拉起数据面、**iam** / **api** / **scheduler** / **agent**、**demo-stack-init**、**console**。IAM 与控制面共用数据库与 Redis（IAM 使用 Redis **db 1**）；默认 **`IAM_DEMO_AUTO_BOOTSTRAP`** 下迁移后幂等创建演示平台用户；**api** 的 **`DEVAULT_IAM_JWKS_URL`** 指向容器内 **iam**；**demo-stack-init** 用 **`DEMO_STACK_PLATFORM_*`** 将 IAM **`demo`** 租户镜像到 DeVault，并在 **`with-agent`** 场景下经 **DeVault REST** 创建演示用 **Agent 令牌**（标签默认 **`demo-stack-agent`**），将 **`plaintext_secret`** 写入命名卷 **`demo_stack_secrets`**（容器内 **`/shared/demo-agent-token`**）；**agent** 通过 **`deploy/scripts/devault-agent-docker-entry.sh`** 从该文件注入 **`DEVAULT_AGENT_TOKEN`**（若已在 **`.env`** 设置 **`DEVAULT_AGENT_TOKEN`** 则优先使用环境变量）。**console** 在 init 成功退出后启动（同源 **`/iam-api`** 反代）。跳过自动令牌：设 **`DEMO_STACK_SKIP_AGENT_TOKEN_BOOTSTRAP=true`** 并自行提供 **`DEVAULT_AGENT_TOKEN`**。默认演示平台账号与覆盖方式见 **`deploy/docker-compose.yml`** 文件头及 **`deploy/.env.stack.example`**（可复制为 **`deploy/.env`**）。

- 控制台：[http://127.0.0.1:8080/](http://127.0.0.1:8080/)  
- IAM OpenAPI：[http://127.0.0.1:8100/docs](http://127.0.0.1:8100/docs)  
- 控制面 API：[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)  

## 可选：多实例 `api`（gRPC 负载均衡）

见 [gRPC 与 API 多实例部署](./grpc-multi-instance.md)。可使用 **`deploy/docker-compose.grpc-ha-example.yml`** 叠加。

## 可选：Prometheus 与 Alertmanager

```bash
cd deploy
docker compose --profile with-control-plane --profile with-agent --profile with-monitoring up -d
```

- Prometheus UI：http://127.0.0.1:9090  
- Alertmanager UI：http://127.0.0.1:9093  

生产接收器见 [可观测性](./observability.md)。

## 服务角色

| 服务 | 说明 |
|------|------|
| **postgres** | 控制面元数据库；DR 见 [控制面元数据库 DR](./control-plane-database-dr.md) |
| **redis** | Redis |
| **minio** | S3 兼容存储 |
| **minio-init** | 一次性 `mc mb` 建桶；运行时**不** `CreateBucket` |
| **iam**（profile **with-control-plane**） | IAM HTTP；与 **api** 共用 Postgres / Redis（Redis **db 1**） |
| **api**（profile **with-control-plane**） | HTTP + gRPC；启动含 `alembic upgrade head`；默认 **`DEVAULT_GRPC_REGISTRATION_SECRET`** 支持 Agent **Register** |
| **scheduler**（profile **with-control-plane**） | Cron 创建任务；**不**跑 `alembic` |
| **agent**（profile **with-agent**） | `DEVAULT_GRPC_TARGET=api:50051`；示例挂载 `deploy/demo_data` → **`/data`**，卷 **`/restore`** |
| **grpc-gateway**（profile **with-grpc-tls**） | Envoy TLS **:50052** → **api:50051** |
| **prometheus** / **alertmanager** / **alertdump**（profile **with-monitoring**） | 本地抓取 **`api:8000/metrics`** 与演示告警路由 |

### Register 引导

默认 Compose 在 **api** 与 **agent** 上使用相同 **`DEVAULT_GRPC_REGISTRATION_SECRET`**。**Register** 成功后 Agent 使用 Redis 颁发的按实例 Bearer。HTTP/UI/CLI 仍用 **`DEVAULT_API_TOKEN`**（默认 `changeme`）。固定 Token 时在 **agent** 上设置 **`DEVAULT_API_TOKEN`**。详见 [配置参考](./configuration.md)。

### Artifact 加密（本地验证）

Compose 中 **agent** 可注入开发用 **`DEVAULT_ARTIFACT_ENCRYPTION_KEY`**；生产须自行生成并保管。含义见 [Artifact 静态加密](../trust/artifact-encryption.md)。

## 构建说明

- 镜像：`deploy/Dockerfile`，`pip install -e .`
- 构建上下文为仓库根目录

## gRPC TLS 与网关

主文件启用 **`--profile with-grpc-tls`**；栈内 Agent 走 TLS 时再 **叠加** **`deploy/compose.include/grpc-tls-agent.yml`**（或 **`docker-compose.grpc-tls.yml`** 包装）（见 [TLS 与网关](../trust/tls-and-gateway.md)）。
