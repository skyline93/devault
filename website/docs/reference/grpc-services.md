---
sidebar_position: 2
title: gRPC（Agent）
description: Agent RPC 与源码位置
---

# gRPC（Agent）

## 接口定义

**`proto/agent.proto`**

修改后：

```bash
bash scripts/gen_proto.sh
```

## 能力与入口

Agent 通过 gRPC **Register / Heartbeat / LeaseJobs / RequestStorageGrant / ReportProgress / CompleteJob** 等完成作业；详见 proto。

[gRPC](../trust/agent-connectivity.md)、[端口速查](./ports-and-paths.md)。

## Register 与会话令牌

成功 **Register** 后控制面在 **Redis** 签发绑定 **`agent_id`** 的 **Bearer**，TTL **`DEVAULT_GRPC_AGENT_SESSION_TTL_SECONDS`**；RPC 成功后刷新 TTL。运维可用 **`POST /api/v1/agents/{agent_id}/revoke-grpc-sessions`** 吊销。

## 版本协商

Agent 携带 **`agent_release`**、**`proto_package`**、**`git_commit`**；控制面返回 **`server_release`**、**`min_supported_agent_version`** 等。

| `devault-reason-code` | 典型 gRPC 状态 |
|-----------------------|----------------|
| `AGENT_VERSION_TOO_OLD` | `FAILED_PRECONDITION` |
| `AGENT_PROTO_PACKAGE_MISMATCH` | `FAILED_PRECONDITION` |
| `AGENT_VERSION_REQUIRED` | `FAILED_PRECONDITION` |
| `AGENT_REGISTRY_MISSING` | `FAILED_PRECONDITION`（LeaseJobs） |

详见 [租户与访问控制](../admin/tenants-and-rbac.md)（gRPC auditor 禁止）、[Agent 舰队](../admin/agent-fleet.md)。

### server_capabilities

**`HeartbeatReply`** / **`RegisterReply`** 带 **`server_capabilities`**（如 **`s3_presign_bundle`**、**`multipart_resume`**）；权威列表见仓库 **`docs/compatibility.json`** 与 [兼容性与版本矩阵](../engineering/compatibility.md)。

### CompleteJob 与恢复演练

**`kind=restore_drill`** 时可填 **`result_summary_json`** → **`jobs.result_meta`**（见 [恢复演练](../user/restore-drill.md)）。

相关环境变量见 [配置参考](../admin/configuration.md) 中 gRPC 小节。
