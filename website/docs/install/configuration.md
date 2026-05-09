---
sidebar_position: 7
title: 配置参考
description: 常用环境变量分组说明
---

# 配置参考

以下为常用变量分组，完整列表以代码内 `pydantic-settings` 定义及 `deploy/docker-compose.yml` 为准。

## 控制面 / API

| 变量 | 说明 |
|------|------|
| `DEVAULT_DATABASE_URL` | SQLAlchemy 数据库 URL（如 `postgresql+psycopg://...`） |
| `DEVAULT_REDIS_URL` | Redis 连接串 |
| `DEVAULT_API_TOKEN` | HTTP Bearer 与简易 UI Basic 密码 |
| `DEVAULT_GRPC_LISTEN` | 绑定 gRPC 的 `host:port`（如 `0.0.0.0:50051`） |
| `DEVAULT_ENV_NAME` | 环境名标签（指标等） |
| `DEVAULT_DEFAULT_TENANT_SLUG` | 未带 `X-DeVault-Tenant-Id` 时按此 slug 解析租户（默认 `default`）；须与迁移种子一致 |
| `DEVAULT_JOB_STUCK_THRESHOLD_SECONDS` | 非终态作业视为「超窗」的秒数（默认 `86400`，范围 `300`–`864000`），驱动 **`devault_jobs_overdue_nonterminal`**；与 [可观测性](./observability.md) 中 Prometheus 告警示例一致 |

### OIDC（可选，Bearer JWT）

与静态令牌、**`control_plane_api_keys`** 并存；Bearer 为 JWT 时优先按 OIDC 校验。详见 [访问控制与 RBAC](../reference/access-control.md)。

| 变量 | 说明 |
|------|------|
| `DEVAULT_OIDC_ISSUER` | 发行方 URL（无尾斜杠亦可），用于 `/.well-known/openid-configuration` |
| `DEVAULT_OIDC_AUDIENCE` | 必填 `aud` |
| `DEVAULT_OIDC_ROLE_CLAIM` | 默认 `devault_role`：`admin` \| `operator` \| `auditor` |
| `DEVAULT_OIDC_TENANT_IDS_CLAIM` | 默认 `devault_tenant_ids`：非 admin 时的租户 UUID 列表 |
| `DEVAULT_SERVER_GIT_SHA` | （可选）写入 **`GET /version`** 的 `git_sha` 字段，便于与镜像 digest 对齐 |

### gRPC 版本策略（控制面）

与 **`proto/agent.proto`** 中 Heartbeat / Register 的 `agent_release` 等字段配合；默认允许未上报版本的旧 Agent（仅返回 `deprecation_message` 提示）。

| 变量 | 说明 |
|------|------|
| `DEVAULT_GRPC_MIN_SUPPORTED_AGENT_VERSION` | 最低可接受 Agent SemVer（默认 `0.1.0`） |
| `DEVAULT_GRPC_MAX_TESTED_AGENT_VERSION` | 最高「已测试」Agent 版本；**空**表示与控制面当前 `version` 相同 |
| `DEVAULT_GRPC_UPGRADE_URL` | （可选）随 gRPC 回复带给 Agent 的升级说明链接 |
| `DEVAULT_GRPC_REQUIRE_AGENT_VERSION` | 设为 `true` 时，未带 `agent_release` 的 Agent 将被拒绝 |
| `DEVAULT_GRPC_ENFORCE_VERSION_ON_LEASE` | 默认 `true`：**`LeaseJobs`** 根据 **`edge_agents`** 表（最近一次 Heartbeat 字段）再次执行版本/proto 校验；紧急绕过可设为 `false` |
| `DEVAULT_GRPC_REGISTRATION_SECRET` | 若设置：开放 **Register**；Agent 可用该密钥换取控制面当前 **`DEVAULT_API_TOKEN`**（**`deploy/docker-compose.yml`** 开发默认与 Agent 侧同值；生产须轮换） |

## 存储后端（S3）

| 变量 | 说明 |
|------|------|
| `DEVAULT_STORAGE_BACKEND` | 设为 `s3` 以启用预签名与 Agent 直传路径 |
| `DEVAULT_S3_ENDPOINT` | S3 API 端点 |
| `DEVAULT_S3_ACCESS_KEY` / `DEVAULT_S3_SECRET_KEY` | 访问密钥（可选；与 AssumeRole / 默认凭证链组合见下） |
| `DEVAULT_S3_ASSUME_ROLE_ARN` | （可选）STS AssumeRole 目标角色；设置后控制面用临时会话密钥访问 S3 |
| `DEVAULT_S3_ASSUME_ROLE_EXTERNAL_ID` | （可选）AssumeRole 的 `ExternalId` |
| `DEVAULT_S3_ASSUME_ROLE_SESSION_NAME` | （可选）默认 `devault-control-plane` |
| `DEVAULT_S3_ASSUME_ROLE_DURATION_SECONDS` | （可选）900–43200，默认 `3600` |
| `DEVAULT_S3_STS_REGION` | （可选）STS 区域，默认同 `DEVAULT_S3_REGION` |
| `DEVAULT_S3_STS_ENDPOINT_URL` | （可选）自定义 STS 端点（如 LocalStack） |
| `DEVAULT_S3_STS_USE_SSL` | （可选）默认 `true` |
| `DEVAULT_S3_BUCKET` | 桶名（须事先存在） |
| `DEVAULT_S3_USE_SSL` | 是否使用 HTTPS |
| `DEVAULT_S3_REGION` | 部分云厂商需要 |

STS、IRSA 与凭证链顺序见 [STS 与 AssumeRole](../storage/sts-assume-role.md)。大对象相关阈值见 [存储调优](../storage/tuning.md)。

## Agent

| 变量 | 说明 |
|------|------|
| `DEVAULT_GRPC_TARGET` | 控制面 gRPC 地址（如 `api:50051`） |
| `DEVAULT_ALLOWED_PATH_PREFIXES` | 逗号分隔路径前缀，如 `/data,/restore` |
| `DEVAULT_API_TOKEN` | 与注册/鉴权相关的令牌（与实现版本一致） |
| `DEVAULT_AGENT_MULTIPART_STATE_DIR` | （可选）Multipart 续传状态与 WIP `bundle.tar.gz` 的根目录；默认 `~/.cache/devault-agent` |
| `DEVAULT_AGENT_GIT_COMMIT` | （可选）随 Heartbeat / Register 上报的短 git SHA |
| `DEVAULT_ARTIFACT_ENCRYPTION_KEY` | （可选）Base64 编码的 32 字节 AES-256 密钥；当策略启用 **`encrypt_artifacts`** 时用于加密备份包及解密恢复；须与运维密钥治理一致 |

详见 [Artifact 静态加密](../security/artifact-encryption.md)。

### Scheduler（`devault-scheduler`）

除 Cron 触发备份外，scheduler 进程执行 **artifact 保留清理**（需能连 **PostgreSQL**、与 **`DEVAULT_STORAGE_BACKEND`** 一致的存储凭证以删除对象）。见 [保留与生命周期](../guides/retention-lifecycle.md)。

| 变量 | 说明 |
|------|------|
| `DEVAULT_RETENTION_CLEANUP_ENABLED` | 默认 `true` |
| `DEVAULT_RETENTION_CLEANUP_INTERVAL_SECONDS` | 默认 `900`（秒），范围 `60`–`86400` |

## 与 Compose 对齐

演示环境默认值见 `deploy/docker-compose.yml`（如 `changeme` Token、MinIO 凭证等）。**生产环境务必替换**。
