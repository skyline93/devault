---
sidebar_position: 2
title: Docker Compose
description: 本地与演示环境的服务角色与启动方式
---

# Docker Compose

仓库在 `deploy/docker-compose.yml` 提供一体化栈，便于快速验证备份/恢复闭环。

## 启动

```bash
cd deploy
docker compose up --build -d
```

## 可选：Prometheus

核心栈不含 Prometheus。需要本地抓取 **`/metrics`** 时，在 `deploy/` 下叠加：

```bash
docker compose -f docker-compose.yml -f docker-compose.prometheus.yml up -d
```

（自仓库根目录请将 `-f` 指向 `deploy/docker-compose.yml` 与 `deploy/docker-compose.prometheus.yml`。）

## 服务角色

| 服务 | 说明 |
|------|------|
| **postgres** | 数据库；健康检查通过后再启动依赖方 |
| **redis** | Redis |
| **minio** | S3 兼容对象存储 |
| **minio-init** | **一次性**任务：使用 `mc mb` 创建桶；应用运行时**不**调用 `CreateBucket`，便于 IAM 最小化 |
| **api** | 控制面：HTTP +（默认开启的）gRPC；启动命令内含 `alembic upgrade head` 与 `uvicorn` |
| **scheduler** | 仅负责按 Cron **创建任务**；**不**执行 `alembic` |
| **agent** | 边缘 Agent：`DEVAULT_GRPC_TARGET=api:50051`，挂载 `demo_data` → `/data`，命名卷 → `/restore` |

**Prometheus** 已拆到独立文件 **`docker-compose.prometheus.yml`**（见上一节），不再随默认 `up` 启动。

### Artifact 加密（可选验证）

Compose 里的 **agent** 默认注入 **`DEVAULT_ARTIFACT_ENCRYPTION_KEY`**（固定开发用 Base64，**非机密**，仅便于本地打开 **`encrypt_artifacts`** 策略时不报错）。生产或共享环境请用 **`openssl rand -base64 32`** 生成并通过环境变量覆盖；密钥只在 **Agent** 侧需要，含义与格式见 [Artifact 静态加密](../security/artifact-encryption.md)。

## 构建说明

- 镜像在 `deploy/Dockerfile` 中通过 `pip install -e .` 安装本仓库
- 构建上下文为仓库根目录；`.dockerignore` 用于缩小上下文

## gRPC TLS 与网关

若需 TLS 终结、Envoy 等叠加文件，可使用仓库提供的 `docker-compose.grpc-tls.yml` 等叠加方式（见 [TLS 与网关](../security/tls-and-gateway.md)）。可与 `docker-compose.prometheus.yml` 同时传入多个 `-f`。
