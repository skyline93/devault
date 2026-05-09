---
sidebar_position: 4
title: 保留与生命周期
description: retention_days、retain_until 与 scheduler 清理任务
---

# 保留与生命周期

DeVault 在 **策略（文件插件）** 上支持可选字段 **`retention_days`**：成功完成备份并登记 artifact 后，控制面将 **`artifacts.retain_until`** 设为「完成时间 + N 天」（UTC）。**未设置**或留空表示**不自动删除**（仅依赖桶侧策略时请仍查阅 [对象存储模型](../storage/object-store-model.md)）。

## 运行时行为

1. **写入**：Agent **`CompleteJob`** 成功后，控制面根据 **当时作业快照** `config_snapshot` 中的 **`retention_days`** 写入 **`retain_until`**。
2. **清理**：**`devault-scheduler`** 进程内定时运行保留清理（默认每 **900** 秒）：扫描 **`retain_until < now()`** 且 **`legal_hold = false`** 的 artifact，按 **`tenant_id`** 解析 **S3 桶与 STS 凭证（BYOB）**，先 **`delete_object`** **bundle** 与 **manifest**，再删除 **PostgreSQL** artifact 行。
3. **指标**：**`devault_retention_artifacts_purged_total`**（按 **`tenant_id`**）、**`devault_retention_purge_errors_total`**。

## 配置（环境变量）

与 API 进程共用 **`DEVAULT_*`** 前缀（scheduler 容器须注入同一数据库与存储相关变量以便 **`get_storage`** 删除对象）：

| 变量 | 说明 |
|------|------|
| `DEVAULT_RETENTION_CLEANUP_ENABLED` | 默认 `true`；设为 `false` 则跳过清理（仅排队备份仍生效）。 |
| `DEVAULT_RETENTION_CLEANUP_INTERVAL_SECONDS` | 清理周期，默认 **900**，范围 **60–86400**。 |

## Legal hold（法务保留）

将 **`artifacts.legal_hold`** 设为 **true** 后，scheduler **不会**因 **`retain_until`** 到期而删除该 artifact（对象与元数据行均保留）。

- **REST**：**`PATCH /api/v1/artifacts/{artifact_id}/legal-hold`**，body **`{"legal_hold": true|false}`**，需 **`admin`** 角色；**`X-DeVault-Tenant-Id`** 须解析为 **该 artifact 所属租户**（与 [访问控制](../reference/access-control.md) 一致）。
- Legal hold 与 **S3 Bucket /Object 级 Legal Hold** 无自动绑定；若需在对象存储侧同步保留，须在云平台另行配置。

对象存储桶上的 **生命周期转换（IA/Glacier）** 仍由运维在云平台配置；DeVault 本条目不替代 **存储类** 迁移，仅负责 **元数据 + 对象删除** 对齐。

## API / UI

- **REST / OpenAPI**：创建策略时在 **`config`** 中传入 **`retention_days`**（正整数）；**`GET /api/v1/artifacts`** 响应含 **`retain_until`**。
- **Web UI**：策略表单 **Retention (days)**；Artifacts 列表展示 **Retain until**。

## 相关文档

- [策略与调度](./policies-and-schedules.md)
- [配置参考](../install/configuration.md)
