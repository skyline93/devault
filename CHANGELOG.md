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
