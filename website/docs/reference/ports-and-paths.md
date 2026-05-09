---
sidebar_position: 3
title: 端口与路径速查
description: 默认端口、HTTP 路由与 Agent 挂载
---

# 端口与路径速查

## 默认端口（Compose 示例）

| 端口 | 服务 |
|------|------|
| **8000** | HTTP、`/docs`、`/ui`、`/metrics` |
| **50051** | gRPC |
| **5432** | PostgreSQL |
| **6379** | Redis |
| **9000** / **9001** | MinIO API / 控制台 |
| **9090** | Prometheus（叠加 `docker-compose.prometheus.yml`） |

网关叠加可能对外暴露 **50052** 等，见 `deploy/docker-compose.grpc-tls.yml`。

## Agent 演示挂载

| 路径 | 说明 |
|------|------|
| **`/data`** | 只读演示数据源 |
| **`/restore`** | 可写恢复 / 演练 |

**`DEVAULT_ALLOWED_PATH_PREFIXES`** 须覆盖实际使用路径。

## 常用 HTTP 路由

| 路径 | 说明 |
|------|------|
| `/docs` | Swagger |
| `/version` | 版本 JSON |
| `/metrics` | Prometheus |
| `/healthz` | 健康检查 |
| `/ui/jobs` | Web 控制台任务 |
