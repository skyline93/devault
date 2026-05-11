---
sidebar_position: 10
title: gRPC 与 API 多实例
description: 水平扩展 api、scheduler 单副本、Envoy LB
---

# gRPC 与 API 多实例

控制面 **api**（HTTP + Agent gRPC）为**无进程内会话**设计：作业与租户数据在 **PostgreSQL**；同策略并发互斥使用 **Redis**。因此可在 LB 后运行 **多个 `api` 副本**。

本文与 [TLS 与网关](../trust/tls-and-gateway.md)、[数据库迁移](./database-migrations.md)、[控制面元数据库 DR](./control-plane-database-dr.md) 互为补充。

## 哪些组件可多副本

| 组件 | 多副本 | 说明 |
|------|--------|------|
| **`api`（HTTP + gRPC）** | ✅ | 共享 DB/Redis |
| **`devault-scheduler`** | ❌ **单副本** | APScheduler 无分布式互斥；多副本会重复创建 Cron 任务。保留清理同理宜单路径为主（见 [保留与生命周期](../user/retention-lifecycle.md)）。 |
| **PostgreSQL / Redis** | HA 自建 | 控制面假定单一逻辑实例 |
| **Agent** | ✅ | 与 `api` 副本数无关 |

## 共享状态与并发

- **租约**：`LeaseJobs` 等对 `jobs` 的原子更新 + 过期回收保证互斥领取。
- **同策略备份互斥**：Redis 键（见 `src/devault/core/locking.py`）。
- **HTTP**：无状态；认证读 DB/JWT。

## gRPC 会话亲和（sticky）

**通常不需要。** 可选时用一致性哈希等到源 IP，仅体验/审计取向。

## `DEVAULT_GRPC_RPS_PER_PEER`（多副本）

令牌桶为 **单进程**阈值；多副本时全局上限约为 **副本数 × 单副本配置**。集群级硬上限建议在 **网关**实现。

## Compose：扩展 `api` 与端口

宿主机映射 `8000`/`50051` 时 **`--scale api=N` 会冲突**。使用 **`deploy/docker-compose.grpc-ha-example.yml`** + TLS 示例：

```bash
./deploy/scripts/compose-grpc-ha-demo.sh
```

或手动叠加 **`compose.include/grpc-tls-agent.yml`**（或 **`docker-compose.grpc-tls.yml`**）与 **`grpc-ha-example.yml`**，并加上 **`--profile with-control-plane --profile with-agent --profile with-grpc-tls`**，再 `up --scale api=3`。

## Envoy 上游与 HTTP

- gRPC：**`deploy/envoy/envoy-grpc-tls.yaml`** — `ROUND_ROBIN`、`STRICT_DNS`、`address: api`
- HTTP：多副本时前加 Ingress/ALB/Nginx，`GET /healthz` 探测

## Kubernetes（概要）

1. **`Deployment api`**：`replicas: N`
2. **Service**：8000、gRPC（或专用网关）
3. **`Deployment scheduler`**：`replicas: 1`
4. **迁移**：单独 Job 跑一次 `alembic upgrade head`（见 [数据库迁移](./database-migrations.md)）
5. **探针**：HTTP `GET /healthz`；gRPC `grpc_health_probe`，服务名 **`devault.agent.v1.AgentControl`**

详见 [gRPC（Agent）](../reference/grpc-services.md)。

## Prometheus

每个 **api** 副本暴露 **`/metrics`**；抓取须覆盖**全部**副本。

## 自检清单

- [ ] 所有副本 **DB / Redis / S3** 环境变量一致
- [ ] **scheduler** 仅一份（或承担重复 Cron 的风险）
- [ ] **迁移**单次执行
- [ ] Agent → gRPC 经 TLS Envoy 或等价 LB

## 相关文件

| 路径 | 用途 |
|------|------|
| `deploy/docker-compose.grpc-ha-example.yml` | 去掉宿主机端口便于 scale |
| `deploy/scripts/compose-grpc-ha-demo.sh` | TLS + HA 演示 |
| `deploy/envoy/envoy-grpc-tls.yaml` | gRPC ROUND_ROBIN |
