---
sidebar_position: 1
title: 对象存储模型
description: 预签名、直传与桶生命周期约定
---

# 对象存储模型

## 预签名与直传

当 `DEVAULT_STORAGE_BACKEND=s3` 时，控制面为 Agent 生成 **预签名 URL**，Agent **直接**与 S3 兼容存储通信上传/下载备份对象，减轻控制面带宽压力。

文件备份对象键包含 **`tenant_id`** 段，与元数据表一致，形如  
`devault/<env>/tenants/<tenant_id>/artifacts/<job_id>/bundle.tar.gz`（及 `manifest.json`）。详见 [租户模型](../reference/tenants.md)。

## 桶须事先存在

应用**不会在运行时调用 `CreateBucket`**，以便：

- IAM 权限收敛到对象读写，无需创建桶权限
- 由 Terraform / 运维在部署前创建与 `DEVAULT_S3_BUCKET` 一致的桶

Docker Compose 通过 **`minio-init`** 一次性服务在 MinIO 就绪后执行 `mc mb --ignore-existing`，随后 **`api` / `agent`** 依赖其成功退出再启动，避免首次 PUT 时桶不存在。

## 密钥与端点

`DEVAULT_S3_*` 环境变量需与对象存储实际部署一致；生产环境推荐使用 **STS AssumeRole** 或节点/Pod 身份替代长期静态密钥，见 [STS 与 AssumeRole](./sts-assume-role.md)。**按租户（BYOB）** 可使用 **`PATCH /api/v1/tenants/{id}`** 配置 **`s3_bucket`** 与可选 **`s3_assume_role_arn`**（及 **ExternalId**），预签名与控制面 **`CompleteMultipartUpload`**、保留清理等均使用该租户解析出的桶与客户角色。详见 [租户模型](../reference/tenants.md)。

**Object Lock**：若策略配置 **`object_lock_mode`** / **`object_lock_retain_days`**，写路径上的预签名与 **CreateMultipartUpload** 将携带合规保留截止日期；桶必须已开启 **Object Lock**（与 [Artifact 加密](../security/artifact-encryption.md) 可叠加）。

跨区域复制、生命周期策略等在存储侧配置，不由 DeVault 替代。

按 **artifact** 的删除与 **`retain_until`**（策略 **`retention_days`**）由控制面元数据与 **`devault-scheduler`** 清理任务执行，见 [保留与生命周期](../guides/retention-lifecycle.md)；可与桶生命周期规则并用（**`legal_hold`** 的 artifact 不会被 DeVault 清理删除）。
