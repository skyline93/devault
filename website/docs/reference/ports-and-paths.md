---
sidebar_position: 3
title: 端口与路径速查
description: 默认端口、HTTP 路由与 Agent 路径约定
---

# 端口与路径速查

## 默认端口（Compose 示例）

| 端口 | 服务 |
|------|------|
| **8000** | HTTP API、Swagger、`/ui`、`/metrics` |
| **50051** | 控制面 gRPC（与 HTTP 同进程时由 api 暴露） |
| **5432** | PostgreSQL |
| **6379** | Redis |
| **9000** / **9001** | MinIO API / 控制台 |
| **9090** | Prometheus（仅在使用 `deploy/docker-compose.prometheus.yml` 叠加时） |

网关叠加时可能对外暴露 **50052** 等 TLS 端口，见 `deploy/docker-compose.grpc-tls.yml`。

## Agent 容器路径（演示）

| 路径 | 说明 |
|------|------|
| **`/data`** | 只读演示数据（仓库 `demo_data` 挂载） |
| **`/restore`** | 可写恢复卷 |

环境变量 **`DEVAULT_ALLOWED_PATH_PREFIXES`** 必须为上述前缀（或你的自定义前缀）的子集，以逗号分隔。

## 常用 HTTP 路由

| 路径 | 说明 |
|------|------|
| `/docs` | Swagger UI |
| `/version` | 版本 JSON |
| `/metrics` | Prometheus |
| `/healthz` | 健康检查 |
| `/ui/jobs` | 简易任务 UI |
