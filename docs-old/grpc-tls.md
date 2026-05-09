# Agent gRPC：TLS、mTLS、Envoy 网关与运维说明

本文描述 **阶段 A**（见 [`enterprise-backlog.md`](./enterprise-backlog.md)）在仓库中的落地方式：控制面内嵌 gRPC、可选 **服务端 TLS / mTLS**、**Envoy TLS 终结**示例、**限流与审计日志**、**Register 引导**、**标准 Health 服务**。

---

## 1. 两种典型拓扑

| 拓扑 | Agent → | 控制面 gRPC | 说明 |
|------|---------|-------------|------|
| **开发默认** | `api:50051` 明文 | `DEVAULT_GRPC_LISTEN` 无 TLS | `docker-compose.yml` 默认，零证书。 |
| **网关 TLS（推荐对外）** | `grpc-gateway:50052` TLS | Envoy 终结 TLS，内网转发 `api:50051` 明文 h2 | 使用 `docker-compose.grpc-tls.yml` 叠加。 |
| **直连 TLS** | `api:50051` TLS | `DEVAULT_GRPC_SERVER_TLS_*` 启用内嵌 TLS | 无 Envoy 时仍加密链路。 |

「明文仅在内网」在叠加 Envoy 时是预期：**TLS 在网关终结**，Docker 网络内为 h2c 至 API。

---

## 2. 环境变量（控制面 / API 进程）

| 变量 | 含义 |
|------|------|
| `DEVAULT_GRPC_LISTEN` | 例如 `0.0.0.0:50051`；不设置则不启动 gRPC。 |
| `DEVAULT_GRPC_SERVER_TLS_CERT_PATH` | 服务端证书 PEM（与 KEY 成对出现）。 |
| `DEVAULT_GRPC_SERVER_TLS_KEY_PATH` | 服务端私钥 PEM。 |
| `DEVAULT_GRPC_SERVER_TLS_CLIENT_CA_PATH` | 若设置：要求 **mTLS**，仅接受该 CA 签发的客户端证书。 |
| `DEVAULT_GRPC_RPS_PER_PEER` | 每 gRPC `peer()` 的令牌桶速率；`0` 关闭（默认）。 |
| `DEVAULT_GRPC_RPS_BURST_PER_PEER` | 桶容量（默认 `40`）。 |
| `DEVAULT_GRPC_AUDIT_LOG` | `true`/`false`：是否对每次 Agent RPC 打 JSON 审计行到 logger `devault.grpc.audit`。 |
| `DEVAULT_GRPC_REGISTRATION_SECRET` | 若设置：开放 `Register` RPC；Agent 用该密钥换取 **Redis 绑定的每-Agent Bearer**（见 §5）。 |
| `DEVAULT_GRPC_AGENT_SESSION_TTL_SECONDS` | `Register` 签发的 Agent gRPC Bearer 在 Redis 中的 TTL（秒）；每次带该 Bearer 的 RPC 会刷新过期时间（默认 7 天）。 |

---

## 3. 环境变量（Agent）

| 变量 | 含义 |
|------|------|
| `DEVAULT_GRPC_TARGET` | `host:port`。 |
| `DEVAULT_GRPC_TLS_CA_PATH` | 信任的服务端/网关 CA PEM；设置后使用 **TLS**。 |
| `DEVAULT_GRPC_TLS_CLIENT_CERT_PATH` / `DEVAULT_GRPC_TLS_CLIENT_KEY_PATH` | 可选，成对出现：向服务端做 **客户端证书**（mTLS）。 |
| `DEVAULT_GRPC_TLS_SERVER_NAME` | 校验证书用的主机名（例如证书 CN 为 `grpc-gateway` 时需设置）。 |
| `DEVAULT_API_TOKEN` | 与 HTTP 相同的 Bearer；若省略且配置了 `DEVAULT_GRPC_REGISTRATION_SECRET`，启动时先调 `Register` 获取 token。 |

---

## 4. 开发证书与 Envoy 叠加

```bash
bash scripts/gen_grpc_dev_tls.sh
docker compose -f deploy/docker-compose.yml -f deploy/docker-compose.grpc-tls.yml up --build
```

证书输出目录：`deploy/tls/dev/`（已在 `.gitignore` 中忽略）。`grpc-gateway` 监听 **50052**（TLS），管理接口 **9901**。

示例 Envoy 配置包含 **`envoy.filters.http.local_ratelimit`**（与进程内 **`DEVAULT_GRPC_RPS_PER_PEER`** 形成双层限流）；参数见文档站 [TLS 与网关](../website/docs/security/tls-and-gateway.md#envoy-边缘限流local_rate_limit)。

`docker-compose.yml` 中 **`api` 配有 `healthcheck`**（轮询 `http://127.0.0.1:8000/healthz`，`start_period` 覆盖 alembic + 冷启动）；**`grpc-gateway` / `agent` / `scheduler`**（以及可选叠加的 **Prometheus**）对 `api` 使用 **`condition: service_healthy`**，避免 Envoy 连上游 `api:50051` 时出现 **connection refused**（容器已起但 gRPC 尚未监听）。

Envoy 下行 TLS 必须在 `common_tls_context` 中声明 **`alpn_protocols`**（含 **`h2`**），否则 Python `grpc.secure_channel` 可能报错：`Cannot check peer: missing selected ALPN property`。仓库内 `deploy/envoy/envoy-grpc-tls.yaml` 已包含该配置。

---

## 5. Register（每 Agent Redis 会话）

- 控制面配置 **`DEVAULT_GRPC_REGISTRATION_SECRET`** 且 **Redis 可达** 时，`Register` 成功后返回 **仅绑定该 `agent_id`** 的 **`bearer_token`**（存于 Redis，TTL **`DEVAULT_GRPC_AGENT_SESSION_TTL_SECONDS`**）；**`expires_in_seconds`** 与之一致。
- Agent 可在 **不设置** `DEVAULT_API_TOKEN` 的情况下仅配置 **`DEVAULT_GRPC_REGISTRATION_SECRET`**，启动时调用 `Register` 将 token 保留在内存。
- 运维仍可使用 **`DEVAULT_API_TOKEN`** 或 **HTTP API Key** 携带 Bearer 调用 Agent gRPC（不按 `agent_id` 绑定会话，用于排障）。
- 管理员可 **`POST /api/v1/agents/{agent_id}/revoke-grpc-sessions`** 吊销某 Agent 全部 Register 会话。
- **安全**：`registration_secret` 与 HTTP 侧 **`DEVAULT_API_TOKEN`** 同级敏感，应轮换；Redis 须受控访问。

---

## 6. 健康检查（Kubernetes）

标准服务 **`grpc.health.v1.Health`** 已注册：

- 服务名 `""`（整体）与 `devault.agent.v1.AgentControl` 均为 **SERVING**。

探针示例（需镜像内带 [grpc_health_probe](https://github.com/grpc-ecosystem/grpc-health-probe) 或等价工具）：

```text
grpc_health_probe -addr=:50051 -service=devault.agent.v1.AgentControl
```

若 gRPC 仅集群内明文、对外经 Envoy TLS，探针通常仍打在 **API Pod 的 50051** 上。

---

## 7. 审计日志

当 `DEVAULT_GRPC_AUDIT_LOG=true`（默认），每条 Agent RPC 结束后由 logger `devault.grpc.audit` 输出一行 JSON，字段包含 `rpc`、`peer`、`grpc_code`、`elapsed_ms`、`extra`（如 `agent_id`）。**不包含** Authorization 或 Register 返回的 token。

将 `devault.grpc.audit` 配置为 JSON handler 或接入集中日志即可对接 SIEM。

---

## 8. HTTP 版本端点

控制面提供 `GET /version`，返回 `service`、`version`（与 `devault.__version__` 一致）、`api`、`grpc_proto_package`，以及可选的 `git_sha`（`DEVAULT_SERVER_GIT_SHA`）；与 gRPC **Heartbeat** / **Register** 中的 `agent_release` / `server_release` 等字段互补，用于发布校验与自动化探测。

---

## 9. 多实例控制面（API + gRPC）

水平扩展 **`api`（HTTP 与同进程的 Agent gRPC）**、共享 **PostgreSQL** 与 **Redis**、**Envoy `ROUND_ROBIN`**、**`devault-scheduler` 必须单副本**、以及 **`DEVAULT_GRPC_RPS_PER_PEER` 为每进程令牌桶**（多副本时全局近似 `N ×` 单副本）等，见文档站 **`website/docs/install/grpc-multi-instance.md`**；演示叠加 **`deploy/docker-compose.grpc-ha-example.yml`** 与 **`deploy/scripts/compose-grpc-ha-demo.sh`**。
