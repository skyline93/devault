---
sidebar_position: 15
description: 周期性自动恢复演练（restore_drill）、Cron 调度与 Agent 侧报告
---

# 自动恢复演练（Restore drill）

**恢复演练**将指定 **artifact** 在边缘 **Agent** 上解压到**隔离目录**，重复校验 bundle/manifest 与备份链路一致的完整性验证路径；成功后写入 JSON **演练报告**，并将摘要存回控制面 **`jobs.result_meta`**。

与手动「恢复到任意目录」的区别：

| | 手动恢复 `POST /jobs/restore` | 演练 `POST /jobs/restore-drill` / Cron |
|--|-------------------------------|----------------------------------------|
| 目标路径 | 调用方指定 `target_path` | **`drill_base_path`/devault-drill-`<job_id>`/**（每 Job 唯一） |
| 用途 | 业务恢复 | **可重复执行的备份可信度验证** |
| 报告 | 无 | Agent 磁盘 **`.devault-drill-report.json`** + API **`result_meta`** |

## 前置条件

- 控制面 **`DEVAULT_STORAGE_BACKEND=s3`**（与现有备份/恢复一致）。
- Agent **`DEVAULT_ALLOWED_PATH_PREFIXES`**（或等价配置）须包含演练目录前缀，例如 Compose 默认中的 **`/restore`**。
- 演练与恢复相同：若 artifact 带 **加密**，Agent 需配置 **`DEVAULT_ARTIFACT_ENCRYPTION_KEY`**。

## 简易 Web UI

在 **`/ui/restore-drill-schedules`** 可 **增删改 Cron 演练调度**；一次性演练请用 API **`POST /api/v1/jobs/restore-drill`**（Artifacts 页面仅保留手动恢复）。任务列表 **`/ui/jobs`** 对成功的 **`restore_drill`** 会摘要显示 **`result_meta.extract_root`**。

## 一次性演练（API）

`POST /api/v1/jobs/restore-drill`

```json
{
  "artifact_id": "550e8400-e29b-41d4-a716-446655440000",
  "drill_base_path": "/restore/drills"
}
```

成功完成后：

- 解压目录：`/restore/drills/devault-drill-<job_id>/`
- 报告文件：同目录下 **`.devault-drill-report.json`**
- `GET /api/v1/jobs/{job_id}` 的 **`result_meta`** 与报告 JSON 内容一致（**`schema`: `devault-restore-drill-report-v1`**）

## 定时演练（devault-scheduler）

1. 创建 **`POST /api/v1/restore-drill-schedules`**，指定 **`artifact_id`**、**`cron_expression`**、**`timezone`**、**`drill_base_path`**。
2. **`devault-scheduler`** 周期性 reload DB（与备份 Cron 相同），为每条启用调度注册 APScheduler 任务（作业 id 前缀 **`rd_`**）。
3. 触发时插入 **`kind=restore_drill`** 的待处理 Job（**`trigger=scheduled`**），由 Agent **`LeaseJobs`** 领取执行。

关闭或删除调度即停止后续演练；已排队 Job 仍可按任务列表取消。

## gRPC 协议

- **Job kind**：**`restore_drill`**（与 **`restore`** 相同走 **`RequestStorageGrant` READ**）。
- **`CompleteJobRequest`** 成功时可携带 **`result_summary_json`**（演练报告 JSON；见 **`proto/agent.proto`**）。

## 运维提示

- **入队执行前**：若 **`devault-drill-<job_id>/`** 已存在且非空（例如上次同一 Job 重试、租约回收后再次领取），Agent 会在**开始下载前**拒绝并返回 **`TARGET_NOT_EMPTY`**；需清空该目录或换新 Job。解压完成后的写报告阶段**不再**做此项检查（与实现 `_resolve_restore_drill_paths` / `_require_restore_drill_workspace_clean` 一致）。
- 每次新 Job 使用新的 **`job_id`** 子目录；重复运行同一 Job 若目录非空会失败（避免静默覆盖）。
- 磁盘占用随 artifact 体积线性增长；定期清理 **`drill_base_path`** 下旧的 **`devault-drill-*`** 目录。
- Prometheus：**`devault_jobs_total{kind="restore_drill",status="success"}`**（亦可按 **`tenant_id`** / **`policy_id`** 分组）；失败演练见 **`status="failed"`** 与 [可观测性](../install/observability.md#backup-integrity-and-sla-alerts) 告警示例。

更多备份/恢复主路径见 [备份与恢复流程](./backup-and-restore.md)。
