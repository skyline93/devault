---
sidebar_position: 3
title: Kubernetes（Helm）
description: 使用官方 Helm Chart 在集群中部署控制面、调度器及演示依赖（PostgreSQL、Redis、MinIO）
---

# Kubernetes（Helm）

仓库提供 **Helm 3** Chart：`deploy/helm/devault`，用于在命名空间内安装 **HTTP + gRPC 控制面**、**`devault-scheduler`（单副本）**，并可选安装 **演示用** PostgreSQL、Redis、MinIO（与仓库根目录 `deploy/docker-compose.yml` 栈等价，**非生产托管服务替代品**）。

调度器与多实例约束见 [gRPC 与 API 多实例部署](./grpc-multi-instance.md)。

---

## 前置条件

- Kubernetes **1.26+**
- Helm **3.12+**
- 已构建镜像：在仓库根目录执行

```bash
docker build -f deploy/Dockerfile -t devault:latest .
```

将 `devault:latest` 推送到集群可拉取的仓库后，在 `values.yaml` 或 `--set` 中设置 `image.repository` / `image.tag`。

---

## 安装

建议使用 **与 Chart 名不同的 Release 名**（例如 `dv`），避免资源前缀出现 `devault-devault-…`：

```bash
helm upgrade --install dv deploy/helm/devault \
  --namespace devault --create-namespace \
  --set image.repository=YOUR_REGISTRY/devault \
  --set image.tag=latest
```

默认从 `values.yaml` 读取演示密钥（`secrets.apiToken`、`postgresql.auth.password` 等）。**任何共享或生产环境请全部替换**（可配合 ExternalSecrets、SealedSecrets 或 `helm --set-file`）。

---

## 验证

```bash
kubectl -n devault rollout status deployment/dv-devault-api
kubectl -n devault port-forward svc/dv-devault-api 8000:8000
curl -sf http://127.0.0.1:8000/healthz
```

Chart 附带 Helm **test** hook，在已安装 Release 上执行：

```bash
helm test dv -n devault
```

---

## 主要 Values

| 路径 | 说明 |
|------|------|
| `image.repository` / `image.tag` | 控制面与调度器（及可选 Agent）共用镜像 |
| `api.replicas` | 控制面副本数（>1 时请配合网关负载均衡，见多实例文档） |
| `postgresql.enabled` | 内嵌 Postgres；若为 `false` 须设置 `devault.databaseUrl` |
| `redis.enabled` / `minio.enabled` | 当前 Chart 版本在二者为 `true` 时生成完整演示栈；关闭需自行改模板或提 Issue |
| `agent.enabled` | 默认 `false`；开启后部署带 `emptyDir` 的演示 Agent（路径前缀见 `agent.allowedPathPrefixes`） |
| `ingress.enabled` | 为 HTTP API 创建 Ingress（gRPC 仍建议集群内或专用网关） |

完整默认值见 `deploy/helm/devault/values.yaml`。

---

## 与 Compose 的差异

- **迁移**：由 **`api` Pod** 启动时执行 `alembic upgrade head`（与 Compose 一致）；**不要**在多个副本上并发跑迁移。
- **MinIO 桶**：由 **`api` initContainer** 使用 `mc mb --ignore-existing` 创建，等价于 Compose 中的 `minio-init`。
- **Agent**：Compose 默认挂载 `demo_data`；Helm 默认不启用 Agent，启用后使用空 `emptyDir` 作为 `/data`，需自行注入备份源（PVC、`hostPath` 等）。

---

## 源码位置

- Chart：`deploy/helm/devault/`
- 镜像构建：`deploy/Dockerfile`
