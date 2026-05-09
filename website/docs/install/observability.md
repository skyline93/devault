---
sidebar_position: 8
title: 可观测性
description: Prometheus、Alertmanager、健康检查与日志
---

# 可观测性

## Prometheus

控制面暴露 **`GET /metrics`**（Prometheus 文本格式）。本地 Compose 示例将 Prometheus 放在 **`deploy/docker-compose.prometheus.yml`**（与主栈叠加使用），抓取目标为 **`api:8000`**（见 `deploy/prometheus.yml`）。

常用排查步骤：

1. 确认 `api` 健康检查已通过
2. 浏览器或 `curl` 访问 `http://<host>:8000/metrics`
3. 在 Prometheus UI 中查询相关指标

与租户/访问控制相关的增量指标包括 **`devault_http_requests_total`**（`method`、`path_template`）与 **`devault_billing_committed_backup_bytes_total`**（`tenant_id`，备份成功提交时）；详见 [访问控制与 RBAC](../reference/access-control.md)。

## Alertmanager（告警路由）

`deploy/prometheus.yml` 配置了 **`alerting.alertmanagers`**，将 firing 的告警发往 **Alertmanager**。叠加 **`deploy/docker-compose.prometheus.yml`** 时会启动：

| 服务 | 端口（宿主机） | 说明 |
|------|----------------|------|
| **prometheus** | `9090` | 抓取 `api:8000/metrics`，加载 `deploy/prometheus/alerts.yml` |
| **alertmanager** | `9093` | 路由、分组、抑制与接收器 |
| **alertdump** | （仅容器网络） | [http-https-echo](https://github.com/mendhak/docker-http-https-echo) 演示 **Webhook** 接收端；`docker compose … logs -f alertdump` 可看到 Alertmanager POST 的 JSON |

启动示例（仓库根目录）：

```bash
docker compose -f deploy/docker-compose.yml -f deploy/docker-compose.prometheus.yml up -d
```

生产环境请编辑 **`deploy/alertmanager.yml`**，将 `receivers.demo.webhook_configs` 替换为 **`slack_configs` / `pagerduty_configs` / `email_configs` / `opsgenie_configs`** 等，并妥善保管密钥（建议用 Docker/K8s Secret 注入而非明文写进仓库）。

**仅抓取、不接 Alertmanager** 时：从 `deploy/prometheus.yml` 中删除整个 **`alerting:`** 小节，避免 Prometheus 反复连接失败。

### Kubernetes（Helm）

在 [Kubernetes（Helm）](./kubernetes-helm.md) 安装中可打开 **`monitoring.enabled=true`**，于集群内创建 Prometheus、Alertmanager 与演示 Webhook（均为 **ClusterIP**）。规则文件由 Chart 内 **`prometheus-alerts.yml`** 提供；若修改仓库 **`deploy/prometheus/alerts.yml`**，请同步更新 Chart 内副本以保持告警一致。

## Backup integrity and SLA alerts

下列指标用于 **连续失败、校验/清单失败、控制面完整性拒绝、超窗未结束作业**、**策略锁争用**与 **保留清理错误** 等场景，由 Prometheus 计算后在 Alertmanager 中路由。

| 指标 | 含义 |
|------|------|
| **`devault_jobs_total`** | 终态作业计数；标签含 **`kind`**、**`plugin`**、**`status`**（`success` \| `failed`）、**`tenant_id`**、**`policy_id`**（无策略时为 `none`）、**`error_class`**（失败时 `integrity` 表示 Agent 上报的校验/manifest 类 **`CHECKSUM_MISMATCH` / `INVALID_MANIFEST`** 等；成功与其它失败为 `none` / `operational`）。 |
| **`devault_backup_integrity_control_rejects_total`** | 控制面在 **`CompleteJob`** 成功路径上因清单读失败、**bundle 与 manifest 校验不一致**、对象缺失、Multipart 完成失败等 **拒绝提交** 的次数；**`reason`** 标签区分具体原因。 |
| **`devault_jobs_overdue_nonterminal`** | Gauge：**`stale_bucket`** = `active_work`（`running` / `uploading` / `verifying` 且超过 **`DEVAULT_JOB_STUCK_THRESHOLD_SECONDS`**）或 `pending_unleased`（长期 `pending`）。阈值见 [配置参考](./configuration.md)。 |
| **`devault_policy_lock_contention_total`** | 同策略备份 **Redis 互斥锁** 争用（跳过或失败）计数；按 **`plugin`** 标签。 |
| **`devault_retention_purge_errors_total`** | 保留策略清理（对象删除或 DB）失败次数。 |
| **`devault_multipart_resume_grants_total`** | 控制面在 **`RequestStorageGrant`** 上为 **进行中 Multipart** 签发「续传」类授权（`ListParts` + 缺失分片预签名）的次数。 |
| **`devault_multipart_encrypted_mpu_completes_total`** | 成功的备份 **`CompleteJob`** 中，bundle 走 **S3 Multipart** 且 manifest 含 **`encryption`**（`encrypt_artifacts`）的完成次数；用于观察大密文包上传闭环。 |

示例告警规则（可按环境调阈值）位于仓库 **`deploy/prometheus/alerts.yml`**，由 **`deploy/prometheus.yml`** 的 **`rule_files`** 加载；叠加 Compose 文件 **`deploy/docker-compose.prometheus.yml`** 已挂载该文件并启用 **Alertmanager**。与 [企业部署参考架构](./enterprise-reference-architecture.md)、[安全白皮书摘要](../security/security-whitepaper.md) 交叉阅读。

**存储配额**：对象存储桶配额、云厂商侧用量告警不在 DeVault 指标内，请在 **S3/MinIO 监控或云监控** 中单独配置。

## 健康检查

HTTP 层提供用于编排的就绪类端点（如 Compose 中使用的 **`/healthz`**）。部署时应将负载均衡/滚动更新与此类端点绑定。

## 版本信息

**`GET /version`** 返回 JSON，至少包含 **`service`**、**`version`**（与 `pyproject.toml` / `devault.__version__` 一致）、**`api`**（当前为 `v1`）、**`grpc_proto_package`**（如 `devault.agent.v1`）。若设置 **`DEVAULT_SERVER_GIT_SHA`**，则多一个 **`git_sha`** 字段。与 Agent 在 gRPC **Heartbeat** / **Register** 上交换的 `server_release` / `agent_release` 互补，便于发布校验与自动化探测。

## 日志

- 容器标准输出：由运行时收集（如 `docker compose logs -f api`）
- 生产建议接入集中日志（与基础设施一致）

## gRPC Health

Agent 侧依赖标准 gRPC Health 语义时，请参考 `proto` 与实现中的 health 服务注册方式（与 [gRPC 服务参考](../reference/grpc-services.md) 交叉阅读）。
