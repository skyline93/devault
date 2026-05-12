# IaC 与批量引导

本目录提供 **OpenAPI 对齐** 的最小示例，减少控制台手工：租户 **Agent 令牌**、**策略** 创建。

## 前置

- 控制面已启动并完成迁移；具有写权限的 **IAM Bearer** 与 **`X-DeVault-Tenant-Id`**。
- 已知 **`tenant_id`**（UUID）。

## 示例脚本

- **`examples/curl-agent-token.sh`**：为租户创建 **`POST /api/v1/agent-tokens`**（响应含一次性明文，配置为边端 **`DEVAULT_AGENT_TOKEN`**）。

## Terraform（可选）

- **`terraform-minimal/`**：`null_resource` + `local-exec` 调用 `curl`，无官方 Terraform Provider 依赖。详见该子目录 **`README.md`**。

权威 REST 契约以 **OpenAPI**（`/docs`）为准；多资源顺序：**租户存在 → Agent 令牌 → 边端 Register → 策略（`bound_agent_id`）**。
