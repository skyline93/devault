---
sidebar_position: 7
title: 恢复演练
description: restore_drill、Cron 调度与演练报告
---

# 恢复演练（Restore drill）

**恢复演练**将指定 **artifact** 在边缘 **Agent** 上解压到**隔离目录**，重复校验 bundle/manifest；成功后写入 JSON **演练报告**，并将摘要存回控制面 **`jobs.result_meta`**。

| | 手动恢复 `POST /jobs/restore` | 演练 `POST /jobs/restore-drill` / Cron |
|--|-------------------------------|----------------------------------------|
| 目标路径 | 调用方指定 `target_path` | **`drill_base_path`/devault-drill-`<job_id>`/** |
| 用途 | 业务恢复 | **可重复的备份可信度验证** |
| 报告 | 无 | Agent 磁盘 **`.devault-drill-report.json`** + **`result_meta`** |

## 前置条件

- 控制面当前激活的 **`storage_profiles.storage_type` 为 `s3`**（预签名与直传）。
- Agent **`DEVAULT_ALLOWED_PATH_PREFIXES`** 包含演练目录前缀（如 **`/restore`**）。
- artifact 加密时 Agent 配置 **`DEVAULT_ARTIFACT_ENCRYPTION_KEY`**。

## Web 控制台

在 **`console/`** 路由 **`/compliance/restore-drill-schedules`** 可管理 Cron 演练调度；一次性演练使用 **`POST /api/v1/jobs/restore-drill`**。

## 一次性演练（API）

`POST /api/v1/jobs/restore-drill`

```json
{
  "artifact_id": "550e8400-e29b-41d4-a716-446655440000",
  "drill_base_path": "/restore/drills"
}
```

成功后：解压目录 `.../devault-drill-<job_id>/`，报告 **`.devault-drill-report.json`**；**`GET /api/v1/jobs/{job_id}`** 的 **`result_meta`** 与报告一致（**`schema`: `devault-restore-drill-report-v1`**）。

## 定时演练

1. **`POST /api/v1/restore-drill-schedules`**：`artifact_id`、`cron_expression`、`timezone`、`drill_base_path`。
2. **`devault-scheduler`** reload DB 并注册 APScheduler 任务（作业 id 前缀 **`rd_`**）。
3. 触发时插入 **`kind=restore_drill`** 的 Job，由 Agent **`LeaseJobs`** 领取。

## gRPC

- **Job kind**：**`restore_drill`**（与 **`restore`** 相同走 **`RequestStorageGrant` READ**）。
- **`CompleteJobRequest`** 成功时可携带 **`result_summary_json`**（见 **`proto/agent.proto`**）。

## 运维提示

- 若 **`devault-drill-<job_id>/`** 已存在且非空，Agent 会在开始下载前拒绝（**`TARGET_NOT_EMPTY`**）；需清空或换新 Job。
- 磁盘占用随 artifact 体积增长；定期清理旧 **`devault-drill-*`** 目录。
- 指标：**`devault_jobs_total{kind="restore_drill",...}`**；告警示例见 [可观测性](../admin/observability.md#backup-integrity-and-sla-alerts)。

更多主路径见 [备份与恢复流程](./backup-and-restore.md)。
