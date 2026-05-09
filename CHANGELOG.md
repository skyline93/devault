# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **自动恢复演练（restore drill）**：**`POST /api/v1/jobs/restore-drill`**、**`/api/v1/restore-drill-schedules`**；**`devault-scheduler`** 注册 **`rd_<uuid>`** Cron；Agent **`restore_drill`** 与恢复相同预签名读路径，解压至 **`drill_base_path`/devault-drill-`<job_id>`/**，写入 **`.devault-drill-report.json`** 并经 **`CompleteJob.result_summary_json`** 回传至 **`jobs.result_meta`**。迁移 **`0008`**；**`proto/agent.proto`** 扩展 **`CompleteJobRequest`**。文档 **`website/docs/guides/restore-drill.md`**。**Web UI**：**`/ui/restore-drill-schedules`**、Jobs 列表演练路径摘要。
- **Agent 舰队 Web UI**：**`/ui/agents`**（HTTP Basic，只读表格；与 **`GET /api/v1/agents`** 同源）；导航入口；**`devault.api.presenters.edge_agent_to_out`** 供 REST/UI 共用。
- **Agent 舰队登记与批量版本策略**：表 **`edge_agents`**（Heartbeat/Register 上报）；**`LeaseJobs`** 默认根据登记记录再次执行 **`evaluate_agent_version_gate`**（**`DEVAULT_GRPC_ENFORCE_VERSION_ON_LEASE`**，可关闭）；**`GET /api/v1/agents`** / **`GET /api/v1/agents/{id}`**；CLI **`devault agent list`**。文档 **`website/docs/reference/agent-fleet.md`**。
- **gRPC / API 多实例部署**：文档 **`website/docs/install/grpc-multi-instance.md`**（扩缩 **`api`**、**`scheduler` 单副本**、`DEVAULT_GRPC_RPS_PER_PEER` 进程级语义、Envoy 负载均衡与 Compose 端口冲突处理）；叠加 **`deploy/docker-compose.grpc-ha-example.yml`**、演示脚本 **`deploy/scripts/compose-grpc-ha-demo.sh`**。
- **控制面元数据库 DR Runbook**：PostgreSQL **`pg_dump` / `pg_restore`** 流程、可选 **PITR** 说明、**RTO/RPO** 规划表；脚本 **`deploy/scripts/control-plane-pg-backup.sh`**、**`deploy/scripts/control-plane-pg-restore.sh`**。文档 **`website/docs/install/control-plane-database-dr.md`**（与 artifact 数据面说明 **`website/docs/guides/backup-and-restore.md`** 区分）。
- **保留与生命周期**：文件策略 **`retention_days`**（可选）；备份完成时写入 **`artifacts.retain_until`**；**`devault-scheduler`** 按 **`DEVAULT_RETENTION_CLEANUP_*`** 定时删除过期 **bundle/manifest** 与元数据；Prometheus **`devault_retention_artifacts_purged_total`**、**`devault_retention_purge_errors_total`**；存储抽象 **`delete_object`**。文档 **`website/docs/guides/retention-lifecycle.md`**；Compose **scheduler** 注入与 **api** 一致的 MinIO 变量。
- **Artifact 静态加密（AES-256-GCM）**：策略 **`encrypt_artifacts`**；Agent **`DEVAULT_ARTIFACT_ENCRYPTION_KEY`**（Base64-32 字节）；分块格式 **`devault-chunked-v1`**；manifest 记录 **`encryption`** 与 **`plaintext_checksum_sha256`**；**`CompleteJob`** 读 manifest 写入 **`artifacts.encrypted`**；恢复侧 **`RequestStorageGrant` READ** 增加 manifest 预签名 GET。文档 **`website/docs/security/artifact-encryption.md`**。
- **访问控制（M1·四）**：**`control_plane_api_keys`** 表与 **`devault-admin create-api-key`**；**`admin` / `operator` / `auditor`** 与租户允许列表；REST/UI 写操作门禁、**`POST /tenants`** 仅 admin；可选 **OIDC JWT**（`DEVAULT_OIDC_*`）；Agent **gRPC 拒绝 auditor**；指标 **`devault_http_requests_total`**、**`devault_billing_committed_backup_bytes_total`**。文档 **`website/docs/reference/access-control.md`**。
- **租户模型（M1）**：`tenants` 表与 **`policies` / `jobs` / `schedules` / `artifacts`** 的 **`tenant_id`** 外键；迁移 **`0005`** 种子 **`default`** 租户；REST **`/api/v1/tenants`** 与请求头 **`X-DeVault-Tenant-Id`**（或 **`DEVAULT_DEFAULT_TENANT_SLUG`**）作用域；S3 对象键含 **`tenants/<tenant_id>/artifacts/<job_id>`**；gRPC 租约 **`config_json`** 含 **`tenant_id`** 供 Agent 推导键。文档 **`website/docs/reference/tenants.md`**。
- **控制面 S3 凭证：STS AssumeRole 与默认链**：`DEVAULT_S3_ASSUME_ROLE_ARN`（及 `EXTERNAL_ID`、`SESSION_NAME`、`DURATION_SECONDS`、`DEVAULT_S3_STS_*`）通过 STS 获取短时会话密钥；与静态 `DEVAULT_S3_ACCESS_KEY`/`SECRET` 或 boto3 默认凭证链（IRSA、实例配置等）组合；AssumeRole 结果带过期前刷新缓存。实现见 **`src/devault/storage/s3_client.py`**；说明见 **`website/docs/storage/sts-assume-role.md`**。
- **发版 SSOT 与脚本**：`pyproject.toml` 的 `[project].version` 为唯一维护处；`devault.__version__` 在安装包上读 `importlib.metadata`，源码/pytest 仅 `PYTHONPATH=src` 时回读仓库根 `pyproject.toml`。新增 **`scripts/bump_release.py`**（将 `[Unreleased]` 折叠进新版本并 bump 版本号）、**`scripts/verify_release_docs.py`**（校验 CHANGELOG 含当前版本节）。CI **`.github/workflows/ci.yml`** 跑 pytest 与校验脚本。
- **gRPC 双端版本协商**：扩展 **`Heartbeat` / `Register`**（`agent_release`、`proto_package`、`git_commit` 与控制面 `server_release`、`min_*`、`max_*`、`upgrade_url`、`deprecation_message`）；不兼容时在 **trailing metadata** `devault-reason-code` 与明确 gRPC 状态。控制面环境变量 **`DEVAULT_GRPC_MIN_SUPPORTED_AGENT_VERSION`** 等；依赖 **`packaging`** 做 SemVer 比较。
- **HTTP `GET /version`**：增加 `api`、`grpc_proto_package`、可选 **`git_sha`**（`DEVAULT_SERVER_GIT_SHA`）。**`devault` / `devault-agent` / `devault-scheduler`** 支持 **`--version` / `-V`**。
- **兼容性与发版**：**`docs/compatibility.json`**（矩阵、`current`、能力表）、**`docs/RELEASE.md`** 模板、**`scripts/verify_compatibility_matrix.py`**（与 **`pyproject.toml`** / **`ALL_KNOWN_SERVER_CAPABILITIES`** 对齐）。CI **`matrix.suite`：`full` | `compatibility`**。gRPC **`server_capabilities`**；文件备份 **`manifest.json`** 增加 **`devault_release`**、**`grpc_proto_package`**；**`devault.release_meta`** 集中 gRPC 包名字符串。
- **`deploy/docker-compose.prometheus.yml`**：可选叠加文件，用于本地 Prometheus 抓取 `api` 的 `/metrics`（默认 `docker compose up` 不再启动 Prometheus）。
- **`jobs.created_at`**（迁移 **`0009`**）：任务入队/创建时间；REST **`JobOut`** 与 **`/ui/jobs`** 列；**`GET /api/v1/jobs`** 与 UI 按 **`created_at` 倒序**；**`LeaseJobs`** 待领取候选按 **`created_at` 正序**（FIFO）。

### Changed

- **Artifacts Web UI**（`/ui/artifacts`）：English-only; **Restore** column is a single button per row; clicking opens a **`<dialog>`** modal with the restore form. Restore-drill actions stay off this page (use **Restore drills** or **`POST /api/v1/jobs/restore-drill`**).
- **`deploy/docker-compose.yml`**：默认在 **api** 上开启 **`DEVAULT_GRPC_REGISTRATION_SECRET`**，**agent** 不再注入 **`DEVAULT_API_TOKEN`**，启动时经 **Register** 换取与 **`DEVAULT_API_TOKEN`** 相同的共享令牌（便于在开发环境验证 Register 与 **`/ui/agents`** 的 Registered 列）。若需恢复旧行为，为 **agent** 显式设置 **`DEVAULT_API_TOKEN`**。

### Deprecated

### Removed

### Fixed

- **恢复演练**：写 **`.devault-drill-report.json`** 前不再重复执行「演练目录必须为空」校验（此前在解压成功后误报 **`TARGET_NOT_EMPTY`**）。实现上拆分为 **`_resolve_restore_drill_paths`**（路径 + 前缀）与 **`_require_restore_drill_workspace_clean`**（仅作业开始时调用）。见 **`src/devault/plugins/file/plugin.py`**。

### Security

---

## [0.4.0] - 2026-05-08

### Added

- **Multipart 跨进程/跨重启续传**：控制面在 `jobs` 表记录进行中的 `UploadId` 与对象尺寸；`RequestStorageGrant` 支持 `resume_bundle_multipart_upload_id`，通过 **ListParts** 仅为缺失分片签发预签名；全部已上传时返回 `bundle_multipart_completed_parts_json` 供 `CompleteJob`。
- **Agent**：大备份 bundle 移至 `~/.cache/devault-agent/multipart/<job_id>/bundle.tar.gz`，`checkpoint.json` 记录分片 ETag；进程重启后对同一租约作业自动续传。环境变量 **`DEVAULT_AGENT_MULTIPART_STATE_DIR`** 可覆盖状态根目录。
- **指标**：`devault_multipart_resume_grants_total`（续传类授权次数）。
- **Alembic**：`0004_job_bundle_multipart_wip` 为 `jobs` 增加 `bundle_wip_*` 列。

### Changed

- **文档**：`docs-old/s3-data-plane.md`、`docs-old/enterprise-backlog.md`、`website/docs/install/configuration.md`、`website/docs/storage/tuning.md` 与 Multipart 续传行为对齐。

### Security

- 续传授权仍校验 **租约 Agent** 与 **job 维度** 的 WIP `UploadId`；新 Multipart 开始前会 **Abort** 控制面记录的孤儿 MPU（同 job、bundle key）。

---

## [0.3.0] - 2026-05-08

### Added

- **文档站**：仓库根目录 `website/` 新增 Docusaurus 3 站点（中文文档，与 `docs-old/docusaurus-information-architecture.md` 信息架构一致）；CI 工作流 `.github/workflows/docs.yml` 对 `website/**` 执行 `npm ci` 与 `npm run build`。
- **S3 Multipart 备份路径**：`RequestStorageGrant` 携带 `bundle_content_length`；超过阈值时返回分片预签名；`CompleteJob` 触发控制面 `complete_multipart_upload`（[`docs/s3-data-plane.md`](docs/s3-data-plane.md)）。
- **配置**：`DEVAULT_S3_MULTIPART_THRESHOLD_BYTES`、`DEVAULT_S3_MULTIPART_PART_SIZE_BYTES`。
- **分片上传重试**：Agent 侧每片 PUT 指数退避。
- **单元测试**：`tests/test_multipart_plan.py`（分片规划与 10k 上限）。

### Changed

- **Agent 备份顺序**：先本地打 tarball，再申请存储授权并上传（支持 Multipart）。
- **单 PUT bundle**：改为从磁盘 **流式** 读取上传，降低内存峰值。
- **预签名恢复**：`httpx` **流式下载** + 分块 SHA-256，避免整包进内存。

### Security

- 预签名仍按 **作业 object key** 签发；STS 仍属后续工作（见 enterprise-backlog 阶段 B P2）。

---

## [0.2.0] - 2026-05-08

### Added

- **Agent gRPC 阶段 A**：可选 **服务端 TLS**（`DEVAULT_GRPC_SERVER_TLS_*`）、可选 **mTLS**（`DEVAULT_GRPC_SERVER_TLS_CLIENT_CA_PATH`）；Agent 侧 **TLS / 客户端证书**（`DEVAULT_GRPC_TLS_*`）。
- **Envoy 示例**：`deploy/envoy/envoy-grpc-tls.yaml` + `deploy/docker-compose.grpc-tls.yml`（TLS 终结于 **50052**）。
- **开发证书脚本**：`scripts/gen_grpc_dev_tls.sh`（输出 `deploy/tls/dev/`，已 gitignore）。
- **每 peer 令牌桶限流**（`DEVAULT_GRPC_RPS_PER_PEER`）与 **JSON 审计日志**（logger `devault.grpc.audit`，`DEVAULT_GRPC_AUDIT_LOG`）。
- **`Register` RPC**：可选引导密钥换取 `DEVAULT_API_TOKEN`；Agent 支持仅配置 `DEVAULT_GRPC_REGISTRATION_SECRET` 启动。
- **标准 gRPC Health**（`grpc.health.v1`）与 HTTP **`GET /version`**。
- 文档：**[`docs/grpc-tls.md`](docs/grpc-tls.md)**。

### Security

- 默认 Compose 仍为 **明文 gRPC**；生产请启用 TLS（直连或经 Envoy），并妥善保管 `DEVAULT_API_TOKEN` / `DEVAULT_GRPC_REGISTRATION_SECRET`。

---

## [0.1.0] - 2026-05-08

### Added

- Initial tracked release line in this changelog (version aligned with `pyproject.toml` / `devault.__version__`).
- File backup and restore (tar.gz, SHA-256, manifest) with policy and schedule CRUD.
- Edge Agent: gRPC pull leases (`LeaseJobs`), presigned storage grants, `CompleteJob` flow.
- Control plane: FastAPI HTTP API, embedded gRPC server, APScheduler worker, PostgreSQL + Redis (policy mutex), Prometheus metrics, CLI and minimal Web UI.
- Docker Compose reference deployment (PostgreSQL, Redis, MinIO, API, scheduler, Agent).

### Changed

- n/a (baseline).

### Security

- Authentication for HTTP and gRPC when `DEVAULT_API_TOKEN` is set (shared bearer token); **not** a substitute for TLS or per-agent credentials in production—see [`docs/enterprise-backlog.md`](docs/enterprise-backlog.md) phase A / I.
