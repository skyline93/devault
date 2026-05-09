---
sidebar_position: 5
title: gRPC 与 API 多实例部署
description: 水平扩展控制面、Etcd 无关共享状态、调度器单副本与 Envoy 负载均衡
---

# gRPC 与 API 多实例部署

DeVault **控制面 API** 进程（FastAPI **HTTP** + 内嵌 **Agent gRPC**）设计为**无进程内业务会话**：作业租约、任务状态与租户数据在 **PostgreSQL**；同一策略下并发备份互斥使用 **Redis**（见下文）。因此可在负载均衡之后运行 **多个 `api` 副本**，向外仍表现为单一控制面。

本文说明与 [**TLS / Envoy**](./docker-compose.md)（[`security/tls-and-gateway.md`](../security/tls-and-gateway.md)）、[**数据库迁移**](./database-migrations.md)、[**控制面元数据库 DR**](./control-plane-database-dr.md) 的关系。

---

## 哪些组件可以多副本

| 组件 | 多副本 | 说明 |
|------|--------|------|
| **`api`（HTTP + gRPC）** | ✅ 推荐按需扩展 | 共享 `DEVAULT_DATABASE_URL`、`DEVAULT_REDIS_URL`；每副本独立监听 `DEVAULT_GRPC_LISTEN`。 |
| **`devault-scheduler`** | ❌ **维持单副本** | 使用进程内 APScheduler 触发 Cron；多副本会在同一时刻**重复创建**定时备份任务（无分布式互斥）。保留策略清理同理宜单路径为主（见 [保留与生命周期](../guides/retention-lifecycle.md)）。 |
| **PostgreSQL / Redis** | 集群或托管服务 | 控制面假定单一逻辑库与单一 Redis；高可用由运维在数据层完成。 |
| **Agent** | 水平扩展（边缘） | 每个 Agent 独立 `agent_id`，与控制面副本数量无关。 |

---

## 共享状态与并发安全（为何要 Redis + PG）

- **作业租约**：`LeaseJobs` 等对 `jobs` 表使用原子更新 + 过期回收（见源码 **`src/devault/grpc/servicer.py`** 中 `try_lease_next_job` / `reclaim_expired_job_leases`），多实例并发领取时由数据库保证同一作业不会被两名 Agent 同时租到。
- **同策略备份互斥**：备份类作业在领取前尝试 **`SET NX`** 风格的 Redis 键（**`src/devault/core/locking.py`**），避免同 `policy_id` 多条备份并行；键对所有 `api` 副本可见。
- **HTTP**：常规无状态请求；认证读 DB/JWT，不依赖某一副本内存。

---

## gRPC 是否需要会话亲和（sticky session）

**通常不需要。** Agent 使用标准 gRPC 调用；单次 RPC 无服务端会话粘性要求，切换副本不会影响租约正确性。

可选亲和的场景：

- 希望审计里的 **`peer`**（下游看到的网关地址）或连接行为长期稳定；
- 与下文 **进程内限流** 一起，希望单一 Agent 流量固定打到同一副本（仍仅改善「体验」，非正确性）。

实践中更常见的是在 **Envoy / Nginx / 云 LB** 上对 **TCP** 或 **HTTP2** 设置 **一致性哈希（如源 IP）**；若开启，请确认健康检查与摘除实例行为符合预期。

---

## 限流：DEVAULT_GRPC_RPS_PER_PEER 为多进程语义

控制面在 **每个 `api` 进程内**维护针对 `context.peer()` 的令牌桶（**`src/devault/grpc/rpc_governance.py`** 中 `TokenBucket`）。

含义：

- `DEVAULT_GRPC_RPS_PER_PEER` / `DEVAULT_GRPC_RPS_BURST_PER_PEER` 是 **单副本** 阈值。
- 多副本且 Agent 连接分散在不同副本时，**同一 Agent 视角下的全局吞吐上限约为「副本数 × 单副本配置」**（近似；取决于负载均衡是否打散连接）。
- 若需要 **集群级严格上限**，应在 **网关**（Envoy `local_rate_limit` 等）或使用 Redis 的全局限流组件实现；当前版本未内置 Redis 级 gRPC 限流。

---

## Docker Compose：扩展 `api` 与端口冲突

默认 `deploy/docker-compose.yml` 将 **`8000` / `50051` 映射到宿主机**。同一主机上将 **`api` 扩展为多实例**时，**多个容器无法共用同一宿主机端口**，`docker compose up --scale api=3` **会失败**。

仓库提供叠加文件 **`deploy/docker-compose.grpc-ha-example.yml`**：

- 去掉 **`api`** 的 `ports` 映射，仅在编排网络内暴露端口；
- 建议与 **`deploy/docker-compose.grpc-tls.yml`** 一起使用：Agent 指向 **`grpc-gateway:50052`**，由 Envoy **`ROUND_ROBIN`** 转发到 **`api:50051`**（Docker 内置 DNS 对扩缩后的 `api` 解析为多地址，Envoy **STRICT_DNS** 会解析出多个 endpoint）。

**一键演示**（需已生成 TLS 材料：`bash scripts/gen_grpc_dev_tls.sh`）：

```bash
./deploy/scripts/compose-grpc-ha-demo.sh
```

或手动：

```bash
docker compose -f deploy/docker-compose.yml \
  -f deploy/docker-compose.grpc-tls.yml \
  -f deploy/docker-compose.grpc-ha-example.yml \
  up --build -d --scale api=3
```

宿主机不再直接访问 `localhost:8000`；可在任一 `api` 容器内探测：

```bash
docker compose -f deploy/docker-compose.yml exec api curl -sS http://127.0.0.1:8000/healthz
```

生产建议在 HTTP 前再加 **Ingress / API 网关**，或仅为运维暴露单一调试入口。

---

## Envoy 上游与 HTTP

- **gRPC**：`deploy/envoy/envoy-grpc-tls.yaml` 中集群 **`lb_policy: ROUND_ROBIN`**、`type: STRICT_DNS`、`address: api` —— 扩缩 `api` 后 Envoy 周期性解析 DNS，将连接分到多个副本。
- **HTTP**：默认 Compose **未**为 HTTP 提供多副本入口；多副本 `api` 时应在前面部署 **HTTP 负载均衡**（Kubernetes `Service`、云 ALB、独立 Nginx 等），健康检查可用 **`GET /healthz`**。

---

## Kubernetes（概要）

典型部署：

1. **`Deployment` `api`**：`replicas: N`，环境变量指向同一 **RDS / Cloud SQL** 与 **Redis**。
2. **`Service` ClusterIP**：对内暴露 **8000** 与 **50051**（若 Ingress 仅代理 HTTP，gRPC 可走专用 Service 或经支持 HTTP/2 的网关）。
3. **`Deployment` `scheduler`**：**`replicas: 1`**。
4. **迁移**：单独 **`Job`** 执行 `alembic upgrade head` 一次后再滚动 **`api`**（与 [数据库迁移](./database-migrations.md) 一致）。
5. **探针**：HTTP `GET /healthz`；gRPC 可选 **`grpc_health_probe`**，服务名 **`devault.agent.v1.AgentControl`**（见 [`reference/grpc-services.md`](../reference/grpc-services.md)）。

---

## Prometheus

每个 **`api`** 副本暴露 **`GET /metrics`**。抓取时应包含 **所有副本**（Kubernetes 按 Pod 自动发现；Compose 下可为每个扩缩容器配置目标或使用聚合代理），避免只看到单实例指标。

---

## 自检清单

- [ ] 所有 `api` 副本 **`DEVAULT_DATABASE_URL` / `DEVAULT_REDIS_URL` / S3 相关变量**一致。
- [ ] **`scheduler` 仅一份**（或承认并接受定时任务重复入队的运维风险）。
- [ ] **迁移**仅在升级流水线中单次执行。
- [ ] **Agent → gRPC**：经 TLS Envoy 或等价 LB，而非依赖宿主机直连单个 `:50051`（扩缩后）。
- [ ] 理解 **gRPC 限流为进程级**；若要集群硬上限，在网关叠加策略。

---

## 相关文件

| 路径 | 用途 |
|------|------|
| `deploy/docker-compose.grpc-ha-example.yml` | 去掉 `api` 宿主机端口，便于 `--scale api=N` |
| `deploy/scripts/compose-grpc-ha-demo.sh` | TLS + HA 叠加并 `api=3` 启动示例 |
| `deploy/envoy/envoy-grpc-tls.yaml` | gRPC **ROUND_ROBIN** 上游 |
