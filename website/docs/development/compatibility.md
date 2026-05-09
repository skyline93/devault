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
| **运行时能力** | 控制面在相同回复中返回 **`server_capabilities`** 字符串列表（如 `multipart_resume`），Agent 可据此做能力探测；权威列表见下文 JSON。 |

## 机器可读矩阵

仓库根 **`docs/compatibility.json`** 与代码中的 **`devault.server_capabilities.ALL_KNOWN_SERVER_CAPABILITIES`** 必须一致；CI 运行 **`python scripts/verify_compatibility_matrix.py`** 做校验。

发版时请将 JSON 内 **`current.control_plane_release`** 更新为与 **`pyproject.toml`** 相同的版本号，并按需在 **`matrices`** 中补充组合说明。

## CI 矩阵

GitHub Actions **`ci.yml`** 使用 **`matrix.suite`**：

- **`full`**：全量 **`pytest`**，并执行 **`verify_release_docs.py`**、**`verify_compatibility_matrix.py`**。
- **`compatibility`**：再次执行上述校验脚本，并仅跑 **`tests/test_proto_contracts.py`**、**`tests/test_agent_version_gate.py`**、**`tests/test_verify_compatibility_matrix.py`**，作为与「契约 / 版本门控」相关的轻量切片（与全量并行，便于快速发现契约回归）。

更重的「多版本镜像」端到端矩阵、发版脚本与 JSON 联动、Agent 侧按 capabilities 降级等，记在 **`docs-old/enterprise-backlog.md`**（**M1 · 三、版本管理** §3.2 末尾 **[ ] 可增强** 行），便于排期。

## 发版模板

见 **`docs/RELEASE.md`**（升级顺序、迁移、回滚、发布后验证），与 [发版与变更记录](./releasing.md) 配合使用。

## Manifest 中的制品方信息

文件插件写入的 **`manifest.json`** 在 **`schema_version`: 1** 基础上包含可选字段 **`devault_release`** 与 **`grpc_proto_package`**，便于审计与跨版本恢复说明；缺少这些字段的旧 artifact 仍视为有效。
