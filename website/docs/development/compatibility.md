---
sidebar_position: 5
title: 兼容性与版本矩阵
description: SemVer 策略、compatibility.json 与 gRPC capabilities
---

# 兼容性与版本矩阵

## 策略摘要

| 维度 | 约定 |
|------|------|
| **应用 SemVer** | 控制面与 Agent 共用 `pyproject.toml` / 同次 tag 的发行线；**同一 MAJOR** 内 **MINOR** 以向后兼容为目标（见 CHANGELOG 中破坏性标注）。 |
| **Protobuf 包** | 当前为 **`devault.agent.v1`**，与应用版本解耦；破坏性 RPC 变更时递增包名（如 `v2`）并走协调升级。 |
| **gRPC 协商** | **`Heartbeat`** / **`Register`** 交换 `agent_release`、`proto_package` 等；运维可用 **`DEVAULT_GRPC_MIN_SUPPORTED_AGENT_VERSION`** 等收紧策略（见 [配置参考](../install/configuration.md)）。 |
| **运行时能力** | 控制面在相同回复中返回 **`server_capabilities`**。Agent **按令牌开关路径**：未宣告 **`multipart_resume`** 则不使用本地 MPU 续传 checkpoint；未宣告 **`multipart_upload`** 则超过阈值仍走单对象预签名 PUT（见 [gRPC 参考](../reference/grpc-services.md) §server_capabilities）。权威列表见下文 JSON。 |

## 机器可读矩阵

仓库根 **`docs/compatibility.json`** 与代码中的 **`devault.server_capabilities.ALL_KNOWN_SERVER_CAPABILITIES`** 必须一致；CI 运行 **`python scripts/verify_compatibility_matrix.py`** 做校验。

发版时请将 JSON 内 **`current.control_plane_release`** 与 **`pyproject.toml`** 对齐。使用 **`python scripts/bump_release.py <版本>`** 时会**自动**写入该字段；手工改版本号时切勿遗漏。

## CI 矩阵

GitHub Actions **`ci.yml`** 使用 **`matrix.suite`**：

- **`full`**：全量 **`pytest`**，并执行 **`verify_release_docs.py`**、**`verify_compatibility_matrix.py`**。
- **`compatibility`**：再次执行上述校验脚本，并仅跑 **`tests/test_proto_contracts.py`**、**`tests/test_agent_version_gate.py`**、**`tests/test_verify_compatibility_matrix.py`**，作为与「契约 / 版本门控」相关的轻量切片（与全量并行，便于快速发现契约回归）。

### 多版本镜像 Compose + gRPC 冒烟

工作流 **`.github/workflows/e2e-version-matrix.yml`**（**`workflow_dispatch`** 与 **每周一 schedule**）按 **`docs/compatibility.json`** 中的 **`ci_e2e`** 定义生成矩阵：

- **`homogeneous`**：控制面镜像与 Agent 镜像均从当前 **`GITHUB_SHA`** 构建；在宿主机与 **Agent 容器内** 各执行一次 **`scripts/e2e_grpc_register_heartbeat.py`**（`Register` + `Heartbeat`），Compose 使用 **`deploy/docker-compose.yml`** 与 **`deploy/docker-compose.e2e-matrix.override.yml`**（预构建镜像，不经由 Compose `build`）。
- 当 **`ci_e2e.previous_minor_git_ref`** 为非空且可解析的 git ref（例如上一 MINOR 的 **`v0.3.0`** tag）时，额外跑两行交叉：**当前 SHA 控制面 + 旧 ref Agent**、**旧 ref 控制面 + 当前 SHA Agent**。ref 留空时仅跑 **`homogeneous`**，避免无 tag 仓库误配导致 nightly 全红。

矩阵语义与 **`matrices[].id`** 的对应关系写在 **`ci_e2e.matrix_definitions`** 中；**`verify_compatibility_matrix.py`** 会校验 **`maps_to_compatibility_rows`** 中的 id 均存在于 **`matrices`**。

§三 **可增强** 中与能力降级、bump 联动相关的历史排期见 **`docs-old/enterprise-backlog.md`**（**M1 · 三** §3.2 与 **§十三**）；已实现项以本站说明为准。

## 发版模板

见 **`docs/RELEASE.md`**（升级顺序、迁移、回滚、发布后验证），与 [发版与变更记录](./releasing.md) 配合使用。

## Manifest 中的制品方信息

文件插件写入的 **`manifest.json`** 在 **`schema_version`: 1** 基础上包含可选字段 **`devault_release`** 与 **`grpc_proto_package`**，便于审计与跨版本恢复说明；缺少这些字段的旧 artifact 仍视为有效。
