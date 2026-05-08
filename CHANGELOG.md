# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

### Deprecated

### Removed

### Fixed

### Security

---

## [0.3.0] - 2026-05-08

### Added

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
