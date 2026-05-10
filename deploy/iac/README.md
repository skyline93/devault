# IaC 与批量引导（§十四-14）

本目录提供 **OpenAPI 对齐** 的最小示例，减少控制台手工：Agent **enrollment**、可选 **Agent 池成员**、**策略** 创建。

## 前置

- 控制面已启动并完成迁移；具有 **admin** 权限的 **`DEVAULT_API_TOKEN`** 或 API Key。
- 已知 **`agent_id`**（UUID）与 **`tenant_id`**（UUID，如 `default` 租户）。

## 示例脚本

- **`examples/curl-enroll.sh`**：为单个 Agent 写入 **`PUT /api/v1/agents/{id}/enrollment`**。

## Terraform（可选）

- **`terraform-minimal/`**：`null_resource` + `local-exec` 调用 `curl`，无官方 Terraform Provider 依赖。详见该子目录 **`README.md`**。

权威 REST 契约以 **OpenAPI**（`/docs`）为准；多资源顺序：**租户存在 → enrollment →（可选）池与成员 → 策略**。
