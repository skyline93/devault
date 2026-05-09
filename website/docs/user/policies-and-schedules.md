---
sidebar_position: 5
title: 策略与定时
description: 策略、Cron 调度与并发语义
---

# 策略与定时

## 策略（Policy）

策略描述**备份什么**与**如何备份**（插件、`config` 等）。HTTP 资源路径为 **`/api/v1/policies`**（详见 OpenAPI）。策略归属某一**租户**；API 通过 **`X-DeVault-Tenant-Id`** 或默认 slug 限定作用域（见 [租户与访问控制](../admin/tenants-and-rbac.md)）。

文件插件 **`config`** 常用可选字段：

| 字段 | 说明 |
|------|------|
| **`retention_days`**（正整数） | 写入 **`artifacts.retain_until`** 并参与 scheduler 清理，见 [保留与生命周期](./retention-lifecycle.md) |
| **`encrypt_artifacts`** | **true** 时备份为密文 tarball；密钥为静态或 **KMS 信封**（见 [Artifact 静态加密](../trust/artifact-encryption.md)） |
| **`kms_envelope_key_id`** | 本策略 KMS CMK，覆盖租户默认与 **`DEVAULT_KMS_ENVELOPE_KEY_ID`** |
| **`object_lock_mode`** | **`GOVERNANCE`** 或 **`COMPLIANCE`**（桶须启用 Object Lock） |
| **`object_lock_retain_days`**（正整数） | 与 **`object_lock_mode`** 同时设置：从写入时刻起算的 **WORM 保留天数** |

`object_lock_mode` 与 `object_lock_retain_days` **须成对**出现。

## 调度（Schedule）

调度将 **Cron 表达式** 与策略绑定，由 **scheduler** 服务周期性地**创建待处理任务**。API 路径为 **`/api/v1/schedules`**。

## 并发与锁

同一策略上可能存在**同策略并发锁**，避免重复全量备份彼此踩踏；具体字段名与行为以 OpenAPI 与实现为准。

## 立即执行

Web 控制台与 API 支持在已有策略上触发立即备份；任务仍走统一队列与 Agent Pull 模型。
