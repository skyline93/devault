---
sidebar_position: 7
title: 兼容性与版本矩阵
description: SemVer、compatibility.json 与 gRPC capabilities
---

# 兼容性与版本矩阵

## 策略摘要

| 维度 | 约定 |
|------|------|
| **SemVer** | 控制面与 Agent 发行对齐；同一 MAJOR 内 MINOR 以兼容为目标（破坏性见 CHANGELOG） |
| **Protobuf 包** | 当前 **`devault.agent.v1`** |
| **gRPC 协商** | **`Heartbeat`** / **`Register`** 上报 `agent_release`、`proto_package` |
| **`server_capabilities`** | 运行时能力令牌；详见 **[gRPC（Agent）](../reference/grpc-services.md)** 与 **`docs/compatibility.json`** |

## 机器可读矩阵

**`docs/compatibility.json`** 与 **`ALL_KNOWN_SERVER_CAPABILITIES`** 必须一致：**`verify_compatibility_matrix.py`** CI 校验。发版时 **`current.control_plane_release`** 与 **`pyproject.toml`** 对齐；推荐 **`bump_release.py`** 自动写入。

## CI 矩阵概要

GitHub Actions **`ci.yml`**：`full` vs `compatibility` 套件。

**`.github/workflows/e2e-version-matrix.yml`**：`homogeneous` 与跨版本 **`previous_minor_git_ref`** smoke，定义见 **`compatibility.json`** → **`ci_e2e`**；**`verify_compatibility_matrix.py`** 校验 id 一致性。

### 后续迭代

能力降级告警、发版脚本与契约矩阵的联动等以 **`CHANGELOG`** 与本页为准持续更新。

## 发版模板

仓库 **`docs/RELEASE.md`**（升级顺序、迁移、回滚）；与本页、[发版与变更记录](./releasing.md) 配合。

## Manifest 可选字段

**`manifest.json`** 可有 **`devault_release`**、**`grpc_proto_package`** 便于审计与跨版本解释；缺失不否定旧 Artifact 的有效性。
