---
sidebar_position: 12
title: 可观测性
description: Prometheus、Alertmanager、健康检查与日志
---

# 可观测性

## Prometheus

控制面 **`GET /metrics`**。Compose 示例 **`deploy/docker-compose.prometheus.yml`** 抓取 **`api:8000`**。

常用租户/用量指标：**`devault_http_requests_total`**、**`devault_billing_committed_backup_bytes_total`**（详见 [租户与访问控制](./tenants-and-rbac.md)）。

## Alertmanager

叠加 Compose 时可启动 Prometheus、Alertmanager、演示 **`alertdump`** Webhook。

生产修改 **`deploy/alertmanager.yml`** 使用 Slack/PagerDuty/邮件等。**仅抓取不接 Alertmanager** 时删除 `prometheus.yml` 中 **`alerting:`** 小节。

Helm：**`monitoring.enabled=true`**（ClusterIP，`port-forward`），规则 **`prometheus-alerts.yml`** 与仓库 **`deploy/prometheus/alerts.yml`** 保持同步。

## Backup integrity and SLA alerts

| 指标 | 含义 |
|------|------|
| **`devault_jobs_total`** | 终态计数；标签 **`kind`、`status`、`tenant_id`、`error_class`** 等 |
| **`devault_backup_integrity_control_rejects_total`** | **`CompleteJob`** 成功路径上控制面完整性拒绝次数 |
| **`devault_jobs_overdue_nonterminal`** | 超窗未结束作业（阈值见 [配置参考](./configuration.md)） |
| **`devault_policy_lock_contention_total`** | 同策略 Redis 锁争用 |
| **`devault_retention_purge_errors_total`** | 保留清理失败 |
| **`devault_multipart_resume_grants_total`** | Multipart 续传授权次数 |
| **`devault_multipart_encrypted_mpu_completes_total`** | 加密 + Multipart 成功完成 |

规则见 **`deploy/prometheus/alerts.yml`**。可与 [企业参考架构](./enterprise-reference-architecture.md)、[安全白皮书摘要](../trust/whitepaper.md) 交叉阅读。

**存储配额**：桶级配额在云监控单独配置。

## 健康检查

编排就绪使用 **`GET /healthz`**。

## 版本信息

**`GET /version`**：`service`、`version`、`api`、`grpc_proto_package`，可选 **`git_sha`**（`DEVAULT_SERVER_GIT_SHA`）。

## 日志

容器 stdout → 运行时收集；生产建议集中日志栈。

## gRPC Health

见 `proto` 与实现注册方式；概要见 [gRPC（Agent）](../reference/grpc-services.md)。
