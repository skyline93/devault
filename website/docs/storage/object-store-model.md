---
sidebar_position: 1
title: 对象存储模型
description: 预签名、直传与桶约定
---

# 对象存储模型

## 预签名与直传

`DEVAULT_STORAGE_BACKEND=s3` 时控制面为 Agent 生成 **预签名 URL**，Agent **直接**与 S3 通信上传/下载。

文件备份对象键含 **`tenant_id`**，形如  
`devault/<env>/tenants/<tenant_id>/artifacts/<job_id>/bundle.tar.gz`（及 `manifest.json`）。见 [租户与访问控制](../admin/tenants-and-rbac.md)。

## 桶须事先存在

应用**不**在运行时 **`CreateBucket`**，以便 IAM 最小化并由 IaC 建桶。

Compose：**`minio-init`** 一次性 `mc mb`。

## 密钥与端点

`DEVAULT_S3_*` 与 STS 见 [STS 与 AssumeRole](./sts-assume-role.md)。按租户 BYOB：**`PATCH /api/v1/tenants`** 配置 **`s3_bucket`**、**`s3_assume_role_arn`**。

**Object Lock**：策略 **`object_lock_mode`** / **`object_lock_retain_days`** 要求桶已启用 Object Lock；可与 [Artifact 加密](../trust/artifact-encryption.md) 叠加。

跨区域复制、生命周期在存储侧配置。按 **`retain_until`** 删除见 [保留与生命周期](../user/retention-lifecycle.md)；**`legal_hold`** 跳过 DeVault 侧删除。
