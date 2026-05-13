---
sidebar_position: 6
title: Kubernetes（Helm）
description: 使用官方 Helm Chart 部署控制面与演示依赖
---

# Kubernetes（Helm）

仓库提供 **Helm 3** Chart：`deploy/helm/devault`，用于安装 **HTTP + gRPC 控制面**、**`devault-scheduler`（单副本）**，并可选安装 **演示用** PostgreSQL、Redis、MinIO（**非生产托管服务替代品**）。

调度器与多实例约束见 [gRPC 与 API 多实例部署](./grpc-multi-instance.md)。

## 前置条件

- Kubernetes **1.26+**
- Helm **3.12+**

```bash
docker build -f deploy/Dockerfile -t glf9832/devault:latest .
```

将镜像推送到集群可拉取仓库后设置 `image.repository` / `image.tag`（Chart 默认 Docker Hub：`glf9832/devault`）。

## 安装

建议使用与 Chart 名不同的 Release 名（例如 `dv`）：

```bash
helm upgrade --install dv deploy/helm/devault \
  --namespace devault --create-namespace \
  --set image.repository=glf9832/devault \
  --set image.tag=latest
```

共享或生产环境请替换全部演示密钥（ExternalSecrets、SealedSecrets 等）。

### 可选：集群内 Prometheus + Alertmanager

```bash
helm upgrade --install dv deploy/helm/devault -n devault \
  --set monitoring.enabled=true
```

见 [可观测性](./observability.md)。Chart 内 **`prometheus-alerts.yml`** 为 `deploy/prometheus/alerts.yml` 的副本，修改时请同步。

## 验证

```bash
kubectl -n devault rollout status deployment/dv-devault-api
kubectl -n devault port-forward svc/dv-devault-api 8000:8000
curl -sf http://127.0.0.1:8000/healthz
helm test dv -n devault
```

## 主要 Values

| 路径 | 说明 |
|------|------|
| `image.repository` / `image.tag` | 控制面与调度器共用镜像 |
| `api.replicas` | >1 时配合网关 LB，见多实例文档 |
| `postgresql.enabled` | `false` 时须 `devault.databaseUrl` |
| `redis.enabled` / `minio.enabled` | 演示栈组件 |
| `agent.enabled` | 默认 `false`；演示 Agent |
| `ingress.enabled` | HTTP Ingress（gRPC 建议专用网关） |
| `monitoring.enabled` | Prometheus、Alertmanager、演示 Webhook |

完整默认值见 `deploy/helm/devault/values.yaml`。

## 与 Compose 的差异

- **`api` Pod** 启动时执行 `alembic upgrade head`；**勿**多副本并发迁移。
- MinIO/S3 **桶**不在 Chart 内创建；请在集群外或 Job 中 **`mc mb`** / 控制台创建，并与 **storage profile** 一致。
- Helm 默认不启用 Agent；启用后为 `emptyDir`，需自备数据源。

## 源码位置

- Chart：`deploy/helm/devault/`
- 镜像：`deploy/Dockerfile`
