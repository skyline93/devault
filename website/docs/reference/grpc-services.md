---
sidebar_position: 2
title: gRPC（Agent）
description: Agent 侧 RPC 与源码位置
---

# gRPC（Agent）

## 接口定义

权威定义在仓库：

**`proto/agent.proto`**

修改后请在仓库根执行（需已安装 `grpcio-tools` 等开发依赖）：

```bash
bash scripts/gen_proto.sh
```

并检查生成代码中的 **相对导入**（如 `from . import agent_pb2`）是否符合当前包结构。

## 能力概述

Agent 通过 gRPC 完成注册、租约拉取、进度上报等；具体 RPC 名称与消息类型以 **`agent.proto`** 为准。

标准 **gRPC Health** 与网关场景下的端口约定见 [Agent 连接](../security/agent-connectivity.md) 与 [端口速查](./ports-and-paths.md)。

## 版本协商（Heartbeat / Register）

Agent 在 **`Heartbeat`** 与 **`Register`** 请求中携带：

- **`agent_release`**：与发行包一致的 SemVer（`devault.__version__`）
- **`proto_package`**：生成代码的包名（如 `devault.agent.v1`）
- **`git_commit`**（可选）：构建注入的短 SHA（`DEVAULT_AGENT_GIT_COMMIT`）

控制面在成功路径的回复中返回 **`server_release`**、**`min_supported_agent_version`**、**`max_tested_agent_version`**、可选 **`upgrade_url`**、**`deprecation_message`**。当 Agent **过旧**、**proto 包不匹配**、或（在开启强制策略时）**未上报版本** 时，RPC 以非 OK 的 gRPC 状态结束，并在 **trailing metadata** 中附带键 **`devault-reason-code`**（与 proto 中 `reason_code` 字符串语义对齐），例如：

| `devault-reason-code` | 典型 gRPC 状态 |
|-----------------------|----------------|
| `AGENT_VERSION_TOO_OLD` | `FAILED_PRECONDITION` |
| `AGENT_PROTO_PACKAGE_MISMATCH` | `FAILED_PRECONDITION` |
| `AGENT_VERSION_REQUIRED` | `FAILED_PRECONDITION` |
| `AGENT_VERSION_UNPARSEABLE` | `INVALID_ARGUMENT` |
| `AGENT_REGISTRY_MISSING` | `FAILED_PRECONDITION`（**`LeaseJobs`**：尚无 **`edge_agents`** 登记记录时；默认需先成功 **`Heartbeat`**） |

登记 **`edge_agents`**、HTTP 查询舰队与 **`LeaseJobs`** 二次校验开关见 [Agent 批量管理与版本策略](./agent-fleet.md)。

相关环境变量见 [配置参考](../install/configuration.md) 中的 **gRPC 版本策略**。

### server_capabilities

**`HeartbeatReply`** 与成功/失败路径上的 **`RegisterReply`** 均携带 **`server_capabilities`** 重复字段，取值来自控制面运行时（如 **`s3_presign_bundle`**、**`multipart_resume`** 等）。权威名称列表与语义说明见仓库 **`docs/compatibility.json`**（`grpc.known_capabilities` 与 `capability_notes`），与 [兼容性与版本矩阵](../development/compatibility.md) 交叉阅读。

Agent 侧行为：**`multipart_resume`** 未出现时不会沿用本地 multipart checkpoint 续传（会清空相关本地状态并重建 tarball）；**`multipart_upload`** 未出现时即使 bundle 超过阈值也不会走「写入 `wip` + MPU」路径，而是使用控制面通过 **`RequestStorageGrant`** 返回的单对象预签名 PUT（若控制面仍宣告 **`s3_presign_bundle`**）。每次成功 **`Heartbeat`** 后刷新 capability 集合（仅 **`HeartbeatReply.ok=true`** 时覆盖；失败则保留上一次集合，例如仍沿用 **`Register`** 时的宣告）。

## CompleteJob 与恢复演练

成功完成 **`kind=restore_drill`** 作业时，Agent 可在 **`CompleteJobRequest`** 中填充 **`result_summary_json`**（与 Agent 磁盘上的 **`.devault-drill-report.json`** 一致的控制面回传字段）；控制面解析后写入 **`jobs.result_meta`**。语义与运维说明见 [自动恢复演练](../guides/restore-drill.md)。
