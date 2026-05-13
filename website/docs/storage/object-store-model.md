---
sidebar_position: 1
title: 对象存储模型
description: 预签名、直传与桶约定
---

# 对象存储模型

## 预签名与直传

当前激活的 **`storage_profiles.storage_type` 为 `s3`** 时，控制面为 Agent 生成 **预签名 URL**，Agent **直接**与 S3 通信上传/下载。

文件备份对象键含 **`tenant_id`**，形如  
`devault/<env>/tenants/<tenant_id>/artifacts/<job_id>/bundle.tar.gz`（及 `manifest.json`）。见 [租户与访问控制](../admin/tenants-and-rbac.md)。

## 桶须事先存在

应用**不**在运行时 **`CreateBucket`**，以便 IAM 最小化并由 IaC 建桶。部署演示栈时请在 MinIO（或生产对象存储）**手工创建**与 **storage profile** 中一致的桶后再跑备份。

## 密钥与端点

S3 兼容连接（端点、区域、桶、SSL、AssumeRole、可选静态密钥）由 **`devault_storage_profiles`** 表与 **`/api/v1/storage-profiles`** 管理；进程级 STS 调优仍见 [STS 与 AssumeRole](./sts-assume-role.md)。**`DEVAULT_STORAGE_CONFIG_MASTER_KEY`** 用于加密 profile 中的静态密钥列。

**Object Lock**：策略 **`object_lock_mode`** / **`object_lock_retain_days`** 要求桶已启用 Object Lock；可与 [Artifact 加密](../trust/artifact-encryption.md) 叠加。

跨区域复制、生命周期在存储侧配置。按 **`retain_until`** 删除见 [保留与生命周期](../user/retention-lifecycle.md)；**`legal_hold`** 跳过 DeVault 侧删除。
