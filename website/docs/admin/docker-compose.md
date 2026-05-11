---
sidebar_position: 5
title: Docker Compose
description: 本地与演示环境的服务角色与启动方式
---

# Docker Compose

仓库在 `deploy/docker-compose.yml` 提供一体化栈。Kubernetes 见 [Kubernetes（Helm）](./kubernetes-helm.md)（`deploy/helm/devault`）。

## 启动

```bash
cd deploy
docker compose pull && docker compose up -d
```

## 控制台 + IAM（本地手测，接近生产链路）

仓库根目录执行 **`make demo-stack-up`**（或 `cd deploy` 后设置 **`DEVAULT_IMAGE=devault:local`** 并 **`docker compose --profile with-console up -d --build`**）：会构建当前代码中的控制面镜像并拉起 **postgres / redis / iam**（IAM 与控制面共用数据库与 Redis；IAM 使用 Redis **db 1**；默认 **`IAM_DEMO_AUTO_BOOTSTRAP`** 下迁移后幂等创建演示平台用户）、**api**（`DEVAULT_IAM_JWKS_URL` 指向容器内 **iam**）、**`demo-stack-init`**（用默认 **`DEMO_STACK_PLATFORM_*`** 将 IAM **`demo`** 租户镜像到 DeVault）、**console**（在 init 成功退出后启动；同源 **`/iam-api`** 反代）。默认演示平台账号与覆盖方式见 **`deploy/docker-compose.yml`** 文件头注释及 **`deploy/.env.stack.example`**（可复制为 **`deploy/.env`**）。

- 控制台：<http://127.0.0.1:8080/>  
- IAM OpenAPI：<http://127.0.0.1:8100/docs>  
- 控制面 API：<http://127.0.0.1:8000/docs>  

## 可选：多实例 `api`（gRPC 负载均衡）

见 [gRPC 与 API 多实例部署](./grpc-multi-instance.md)。可使用 **`deploy/docker-compose.grpc-ha-example.yml`** 叠加。

## 可选：Prometheus 与 Alertmanager

```bash
docker compose -f docker-compose.yml -f docker-compose.prometheus.yml up -d
```

（在 `deploy/` 目录下指定 `-f` 路径。）

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
| **api** | HTTP + gRPC；启动含 `alembic upgrade head`；默认 **`DEVAULT_GRPC_REGISTRATION_SECRET`** 支持 Agent **Register** |
| **scheduler** | Cron 创建任务；**不**跑 `alembic` |
| **agent** | `DEVAULT_GRPC_TARGET=api:50051`；示例挂载 `deploy/demo_data` → **`/data`**，卷 **`/restore`** |

### Register 引导

默认 Compose 在 **api** 与 **agent** 上使用相同 **`DEVAULT_GRPC_REGISTRATION_SECRET`**。**Register** 成功后 Agent 使用 Redis 颁发的按实例 Bearer。HTTP/UI/CLI 仍用 **`DEVAULT_API_TOKEN`**（默认 `changeme`）。固定 Token 时在 **agent** 上设置 **`DEVAULT_API_TOKEN`**。详见 [配置参考](./configuration.md)。

### Artifact 加密（本地验证）

Compose 中 **agent** 可注入开发用 **`DEVAULT_ARTIFACT_ENCRYPTION_KEY`**；生产须自行生成并保管。含义见 [Artifact 静态加密](../trust/artifact-encryption.md)。

## 构建说明

- 镜像：`deploy/Dockerfile`，`pip install -e .`
- 构建上下文为仓库根目录

## gRPC TLS 与网关

叠加 **`deploy/docker-compose.grpc-tls.yml`** 等（见 [TLS 与网关](../trust/tls-and-gateway.md)）。
