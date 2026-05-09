---
sidebar_position: 6
title: Artifact 静态加密（AES-GCM）
description: 静态 DEK、KMS 信封、强制加密与 manifest
---

# Artifact 静态加密（AES-GCM）

对象存储中的 **bundle** 可在上传前由 Agent 使用 **AES-256-GCM** 分层加密（**`devault-chunked-v1`**）；控制面 **不落明文 DEK**。`CompleteJob` 读取 manifest 校验并写入 **`artifacts.encrypted`**。

## 两种密钥路径

| 路径 | 说明 | manifest `encryption` |
|------|------|------------------------|
| **静态 DEK** | Agent：**`DEVAULT_ARTIFACT_ENCRYPTION_KEY`**（Base64-32 字节） | 含 `algorithm`、`format`、`chunk_size_bytes`、`aad`；**无** `key_wrap` |
| **KMS 信封** | Agent：**`kms:GenerateDataKey`** / **`kms:Decrypt`** | **`key_wrap: kms`**，含 **`kms_key_id`**、**`kms_ciphertext_blob_base64`** |

须为 **Agent 身份**授权 **`kms:GenerateDataKey`** 与 **`kms:Decrypt`**。策略 **`encrypt_artifacts: true`** 时启用加密。CMK 解析顺序：

1. 策略 **`kms_envelope_key_id`**
2. 租户 **`kms_envelope_key_id`**
3. **`DEVAULT_KMS_ENVELOPE_KEY_ID`**

## 强制加密

- 全局：**`DEVAULT_REQUIRE_ENCRYPTED_ARTIFACTS=true`**
- 租户：**`require_encrypted_artifacts`**（admin `PATCH /tenants`）

不满足时创建策略或备份会 **400**。

## 静态 DEK 启用

1. 策略 **`encrypt_artifacts: true`**
2. Agent **`DEVAULT_ARTIFACT_ENCRYPTION_KEY`**

**Multipart**：密文大小 ≥ **`DEVAULT_S3_MULTIPART_THRESHOLD_BYTES`** 时走分片；checkpoint 须与 **`encryption`** 块一致（见 [大对象与恢复](../storage/large-objects.md)）。

恢复：READ 授权后 KMS 路径需 **`kms:Decrypt`**；静态路径需同一 **`DEVAULT_ARTIFACT_ENCRYPTION_KEY`**。

## Manifest 与数据库

- **`encryption`**：`algorithm`（`aes-256-gcm`）、`format`（`devault-chunked-v1`）等。
- KMS 额外：`key_wrap`、`kms_key_id`、`kms_ciphertext_blob_base64`。
- **`artifacts.encrypted`**：仅 chunked 密文时为 true。

## Object Lock（WORM）与加密

策略 **`object_lock_mode`** + **`object_lock_retain_days`**：预签名与 **CreateMultipartUpload** 携带 Retention（桶须 Object Lock）。与加密正交。

## 密钥治理

| 主题 | 说明 |
|------|------|
| 生成静态密钥 | `openssl rand -base64 32` |
| 轮换 | 旧 artifact 须原 KMS/密钥恢复 |

## 相关文档

- [配置参考](../admin/configuration.md)
- [租户与访问控制](../admin/tenants-and-rbac.md)
- [策略与定时](../user/policies-and-schedules.md)
- [备份与恢复流程](../user/backup-and-restore.md)
