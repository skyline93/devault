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
| **prometheus**（可选） | 抓取指标示例配置 |

## 构建说明

- 镜像在 `deploy/Dockerfile` 中通过 `pip install -e .` 安装本仓库
- 构建上下文为仓库根目录；`.dockerignore` 用于缩小上下文

## gRPC TLS 与网关

若需 TLS 终结、Envoy 等叠加文件，可使用仓库提供的 `docker-compose.grpc-tls.yml` 等叠加方式（见 [TLS 与网关](../security/tls-and-gateway.md)）。
