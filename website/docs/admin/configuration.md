---
sidebar_position: 8
title: 配置参考
description: 常用环境变量分组说明
---

# 配置参考

以下为常用变量分组，完整列表以代码内 `pydantic-settings` 定义及 `deploy/docker-compose.yml` 为准。

## 控制面 / API

| 变量 | 说明 |
|------|------|
| `DEVAULT_DATABASE_URL` | SQLAlchemy 数据库 URL |
| `DEVAULT_REDIS_URL` | Redis 连接串 |
| `DEVAULT_API_TOKEN` | HTTP Bearer 与 Web UI Basic 密码 |
| `DEVAULT_GRPC_LISTEN` | gRPC `host:port`（如 `0.0.0.0:50051`） |
| `DEVAULT_ENV_NAME` | 环境标签（指标等） |
| `DEVAULT_DEFAULT_TENANT_SLUG` | 未带 `X-DeVault-Tenant-Id` 时按 slug 解析租户 |
| `DEVAULT_JOB_STUCK_THRESHOLD_SECONDS` | 非终态作业「超窗」秒数，驱动 **`devault_jobs_overdue_nonterminal`**（见 [可观测性](./observability.md)） |
| `DEVAULT_FLEET_AGENT_STALE_SECONDS` | **`edge_agents`** 超过该秒数未 **`last_seen_at`** 更新则计入 **`devault_edge_agents_stale_count`**（Prometheus 自定义采集器；告警见 `deploy/prometheus/alerts.yml`） |

### OIDC（可选，Bearer JWT）

与静态令牌、**`control_plane_api_keys`** 并存。详见 [租户与访问控制](./tenants-and-rbac.md)。

| 变量 | 说明 |
|------|------|
| `DEVAULT_OIDC_ISSUER` | 发行方 URL |
| `DEVAULT_OIDC_AUDIENCE` | 必填 `aud` |
| `DEVAULT_OIDC_ROLE_CLAIM` | 默认 `devault_role` |
| `DEVAULT_OIDC_TENANT_IDS_CLAIM` | 默认 `devault_tenant_ids` |
| `DEVAULT_SERVER_GIT_SHA` | 可选：`GET /version` 中 `git_sha` |

### gRPC 版本策略（控制面）

与 **`proto/agent.proto`** 中 Heartbeat / Register 的 `agent_release` 等配合。

| 变量 | 说明 |
|------|------|
| `DEVAULT_GRPC_MIN_SUPPORTED_AGENT_VERSION` | 最低可接受 Agent SemVer（默认 `0.1.0`） |
| `DEVAULT_GRPC_MAX_TESTED_AGENT_VERSION` | 最高已测试 Agent 版本；空表示与控制面版本相同 |
| `DEVAULT_GRPC_UPGRADE_URL` | （可选）随 gRPC 返回的升级说明链接 |
| `DEVAULT_GRPC_REQUIRE_AGENT_VERSION` | `true` 时拒绝无 `agent_release` 的 Agent |
| `DEVAULT_GRPC_ENFORCE_VERSION_ON_LEASE` | 默认 `true`：`LeaseJobs` 再次校验版本 |
| `DEVAULT_GRPC_REGISTRATION_SECRET` | 若设置：开放 **Register** |
| `DEVAULT_GRPC_AGENT_SESSION_TTL_SECONDS` | Register 令牌 Redis TTL（默认 7 天） |

## 存储后端（S3）

| 变量 | 说明 |
|------|------|
| `DEVAULT_STORAGE_BACKEND` | `s3` 启用预签名与 Agent 直传 |
| `DEVAULT_S3_ENDPOINT` | S3 API 端点 |
| `DEVAULT_S3_ACCESS_KEY` / `DEVAULT_S3_SECRET_KEY` | （可选）静态密钥 |
| `DEVAULT_S3_ASSUME_ROLE_ARN` | （可选）STS AssumeRole 目标 ARN |
| `DEVAULT_S3_ASSUME_ROLE_EXTERNAL_ID` | （可选） |
| `DEVAULT_S3_ASSUME_ROLE_SESSION_NAME` | （可选）默认 `devault-control-plane` |
| `DEVAULT_S3_ASSUME_ROLE_DURATION_SECONDS` | （可选）900–43200，默认 `3600` |
| `DEVAULT_S3_STS_REGION` / `DEVAULT_S3_STS_ENDPOINT_URL` / `DEVAULT_S3_STS_USE_SSL` | STS 客户端 |
| `DEVAULT_S3_BUCKET` | 全局默认桶名 |
| `DEVAULT_S3_USE_SSL` | HTTPS |
| `DEVAULT_S3_REGION` | 区域 |

详见 [STS 与 AssumeRole](../storage/sts-assume-role.md)、[租户与访问控制](./tenants-and-rbac.md)（按租户 BYOB）、[存储调优](../storage/tuning.md)。

## Artifact 加密与合规（控制面）

| 变量 | 说明 |
|------|------|
| `DEVAULT_REQUIRE_ENCRYPTED_ARTIFACTS` | `true` 时成功备份要求 chunked 密文 manifest |
| `DEVAULT_KMS_ENVELOPE_KEY_ID` | （可选）默认 KMS CMK；信封操作在 **Agent** |
| `DEVAULT_KMS_REGION` | （可选）KMS 区域 |

详见 [Artifact 静态加密](../trust/artifact-encryption.md)。

## Agent

| 变量 | 说明 |
|------|------|
| `DEVAULT_GRPC_TARGET` | gRPC 地址 |
| `DEVAULT_ALLOWED_PATH_PREFIXES` | 逗号分隔路径前缀 |
| `DEVAULT_API_TOKEN` | Register/鉴权（与版本一致） |
| `DEVAULT_AGENT_MULTIPART_STATE_DIR` | Multipart 状态目录 |
| `DEVAULT_AGENT_GIT_COMMIT` | （可选）上报 git SHA |
| `DEVAULT_ARTIFACT_ENCRYPTION_KEY` | （可选）Base64 AES-256 静态 DEK |

### Scheduler

| 变量 | 说明 |
|------|------|
| `DEVAULT_RETENTION_CLEANUP_ENABLED` | 默认 `true` |
| `DEVAULT_RETENTION_CLEANUP_INTERVAL_SECONDS` | 默认 `900` |

保留清理需在 `s3` 模式下能按租户访问桶（见 [保留与生命周期](../user/retention-lifecycle.md)）。

## 与 Compose 对齐

演示默认值见 `deploy/docker-compose.yml`。**生产务必替换密钥与令牌。**
