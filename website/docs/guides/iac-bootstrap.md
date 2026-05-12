---
sidebar_position: 35
title: IaC 与批量引导（Agent / 池 / 策略）
description: OpenAPI 顺序、curl 与可选 Terraform 最小示例（§十四-14）
---

# IaC 与批量引导

企业环境常用 **GitOps / Terraform / Ansible** 维护 **Agent enrollment**、**Agent 池** 与 **策略**，避免仅依赖 Web 控制台。

## 推荐顺序

1. 租户已存在（迁移 **`0005`** 种子行或 **`POST /api/v1/tenants`**；与 IAM 联调时可传 **`id`** 与 IAM 租户 UUID 对齐）。
2. **`PUT /api/v1/agents/{agent_id}/enrollment`**（**admin**）：非空 **`allowed_tenant_ids`**。
3. （可选）**`POST /api/v1/agent-pools`**、**`PUT .../members`**。
4. **`POST /api/v1/policies`**（写角色）：文件策略 **`config.paths`** 等；若租户 **`policy_paths_allowlist_mode=enforce`**，路径须落在已登记 Agent 的 Heartbeat allowlist 并集内。

OpenAPI 权威定义见 **`/docs`**（或文档站 [gRPC 与端口](../reference/ports-and-paths.md) 中的 HTTP 基址说明）。

## 仓库内示例

| 路径 | 说明 |
|------|------|
| **`deploy/iac/examples/curl-agent-token.sh`** | 创建租户 Agent 令牌的 `curl` 模板 |
| **`deploy/iac/terraform-minimal/`** | `null_resource` + `local-exec` 的最小 Terraform（无专用 Provider） |

与 **§十四-11** 路径预检、**§十四-12** 作业 hostname 快照等能力正交；预检使用 **`POST /api/v1/jobs/path-precheck`** 见 [Agent 舰队](../admin/agent-fleet.md)。
