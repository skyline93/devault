---
sidebar_position: 10
title: Web 控制台与 REST 交付节奏（E-UX-001 / 十四-16）
description: 竖切同期闭合或豁免登记；与 OpenAPI、RBAC、CHANGELOG 闸门（十四-17）互链
---

# Web 控制台与 REST 交付节奏（**E-UX-001** / **十四-16**）

## 原则

凡涉及 **§十四**（多 Agent / 多租户执行隔离）及控制台相关能力：

1. **同一发布周期**内尽量 **竖切交付**：**REST（OpenAPI）** 与 **`/ui/*` 最小可用面** 同期上线。
2. 若当次变更 **仅合并 API**（无 UI），必须在 **PR 描述**中登记 **豁免**：原因、计划中的 UI 回填、目标截止或跟踪 issue；并更新本页 **[豁免台账](#豁免台账)**（或链接到 issue 后在本页只保留一行摘要）。
3. **用户可见行为**（新字段、新 Job 类型、RBAC 语义变化）必须写入 **`CHANGELOG.md`** 的 **`[Unreleased]`**（见仓库根 **`CONTRIBUTING.md`**）。

与 **十四-17**（OpenAPI ↔ 模板、**auditor** 只读、CI 校验）共用 **`CONTRIBUTING.md`** 与 **`.github/pull_request_template.md`** 清单。CI 在 **`pytest`** 前运行 **`python scripts/verify_ui_openapi_registry.py`**，对 **`jobs.html` / `policies.html`** 等模板做关键字段与 **`auth_ctx.can_write()`** 闸门子串检查；**`/ui/*`** 写按钮与表单须与 **`require_write_ui`** 语义一致（只读角色下禁用或隐藏）。

## 豁免台账

| 能力域 | 状态 | 说明 / 跟踪 |
|--------|------|-------------|
| §十四 · 01～14 与相关 UI | **已同期** | 当前仓库 **`/ui/*`** 已覆盖 enrollment、舰队、租户 Agent、策略绑定、路径预检、作业 hostname 等；豁免 **无开放项**。 |
| 后续仅 API 变更 | — | 出现时在 PR 登记并追加一行上表。 |

## 相关文档

- [IaC 与批量引导](./iac-bootstrap.md)（**十四-14**）
- [Web 控制台（用户向）](../user/web-console.md)
- [租户与 RBAC](../admin/tenants-and-rbac.md)
- [Agent 舰队](../admin/agent-fleet.md)
