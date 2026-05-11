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
| **9090** | Prometheus（主 `docker-compose.yml`，profile **`with-monitoring`**） |

网关 **50052** / **9901** 见主 `docker-compose.yml` profile **`with-grpc-tls`**；Agent TLS 片段见 **`deploy/compose.include/grpc-tls-agent.yml`**（或 **`docker-compose.grpc-tls.yml`** 包装）。

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
| `console/`（默认 `:8010`） | Ant Design Pro 控制台（见仓库 **`console/README.md`**） |
