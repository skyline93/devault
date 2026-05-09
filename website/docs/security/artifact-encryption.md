---
sidebar_position: 4
title: Artifact 静态加密（AES-GCM）
description: 静态 DEK、KMS 信封、强制加密策略与 manifest 字段
---

# Artifact 静态加密（AES-GCM）

对象存储中的 **bundle** 可在上传前由 Agent 使用 **AES-256-GCM** 分层加密（**`devault-chunked-v1`**）；控制面 **不落明文 DEK**。`CompleteJob` 时读取 **manifest** 校验校验和，并按 manifest 是否为标准 chunked 密文写入 **`artifacts.encrypted`**。

## 两种密钥路径

| 路径 | 谁在何时用到密钥 | manifest `encryption` |
|------|------------------|------------------------|
| **静态 DEK** | Agent：**`DEVAULT_ARTIFACT_ENCRYPTION_KEY`**（Base64-32 字节），加密与恢复均需同一密钥 | 含 `algorithm`、`format`、`chunk_size_bytes`、`aad`；**无** `key_wrap` |
| **KMS 信封** | **Agent**：在完成 tarball 后的加密步骤中调用 **`kms:GenerateDataKey`**；恢复时对 **`kms_ciphertext_blob_base64`** 调用 **`kms:Decrypt`** 得到 DEK 再解密 bundle（均使用 Agent 侧的 AWS 凭证链 / `DEVAULT_KMS_REGION`）。 | **`key_wrap: kms`**，并含 **`kms_key_id`**、**`kms_ciphertext_blob_base64`** |

信封路径下 **DEK 明文仅瞬时存在于 Agent 进程内存**，与静态路径相同的上传语义。须为 **Agent 身份**授予 **`kms:GenerateDataKey`** 与 **`kms:Decrypt`**（及 CMK 密钥策略）。

启用加密仍须在策略 **`config`** 中将 **`encrypt_artifacts`** 设为 `true`。信封目标 CMK 解析顺序：

1. 策略 **`kms_envelope_key_id`**（若设置）
2. 否则租户 **`kms_envelope_key_id`**（`PATCH /api/v1/tenants/{id}`）
3. 否则环境变量 **`DEVAULT_KMS_ENVELOPE_KEY_ID`**

若以上皆无且未配置 **`DEVAULT_ARTIFACT_ENCRYPTION_KEY`**，备份将失败并报 **密钥缺失**。**注意**：KMS CMK ID 可由租约下发的 **`kms_envelope_key_id`**（来自租户默认值）提供，未必依赖本机 **`DEVAULT_KMS_ENVELOPE_KEY_ID`**。

## 强制加密（策略与租户）

- **全局**：**`DEVAULT_REQUIRE_ENCRYPTED_ARTIFACTS=true`** 时，凡备份 **`CompleteJob` 成功** 的路径上，manifest 必须是 **AES-GCM chunked 密文**（与历史「仅布尔 `encryption`」区分，实现校验 `algorithm`/`format`）。
- **租户**：数据库字段 **`tenants.require_encrypted_artifacts`**（经 admin **`PATCH /api/v1/tenants/{id}`** 开启）时同样要求。**创建/更新策略**与**带内联 config 创建备份作业**若未勾选 **`encrypt_artifacts`**，API 会直接 **400**。

详见 [配置参考](../install/configuration.md) 与本页上文 KMS 段落。

## 启用方式（静态 DEK）

1. **策略配置**：文件备份策略 **`encrypt_artifacts: true`**。
2. **Agent**：设置 **`DEVAULT_ARTIFACT_ENCRYPTION_KEY`**。
3. 若同时配置了 KMS 默认/租户/策略 CMK且满足信封条件，信封路径优先（见上文解析顺序）。

**大对象（Multipart）**：当密文大小 ≥ `DEVAULT_S3_MULTIPART_THRESHOLD_BYTES` 时，Agent 将 **已加密** 的 bundle 走分片上传；`checkpoint.json` 中的 manifest **必须**带 `encryption` 块，且与策略 **`encrypt_artifacts`** 一致。续传前若 **策略与 manifest 不一致** 或 **WIP 字节数与 checkpoint 不符**，Agent 会丢弃 checkpoint/WIP 并重建（见 **`multipart_resume`**）。数据面细节见 [大对象与恢复](../storage/large-objects.md)。

恢复：控制面 **`RequestStorageGrant`（READ）** 预签名 bundle 与 manifest；Agent 读取 manifest 后：**KMS** 路径需 Agent 凭证可 **`kms:Decrypt`**（与备份同一 CMK）；静态路径需 **`DEVAULT_ARTIFACT_ENCRYPTION_KEY`**。

## Manifest 与数据库

静态路径示例字段：

- **`encryption`**：`algorithm`（`aes-256-gcm`）、`format`（`devault-chunked-v1`）、`chunk_size_bytes`、`aad`。

KMS 路径额外：`key_wrap`、`kms_key_id`、`kms_ciphertext_blob_base64`（标准 Base64 的 KMS **CiphertextBlob**）。

**`plaintext_checksum_sha256`** / **`plaintext_size_bytes`**：内层 tarball 的校验信息与大小。

**`artifacts.encrypted`**：仅在 manifest 满足 **chunked 密文格式** 时为 **true**（避免误标）。

## Object Lock（WORM）与加密

若在策略中配置 **`object_lock_mode`** + **`object_lock_retain_days`**，预签名 PUT 与 **CreateMultipartUpload** 会携带 **Retention** 截止日期（桶须开启 Object Lock）。与加密正交：**bundle 仍可加密**，保留策略作用于对象锁定元数据。

## 密钥治理（运维）

| 主题 | 说明 |
|------|------|
| **静态密钥生成** | `openssl rand -base64 32` |
| **轮换** | 新密钥/KMS CMK 只影响新备份；旧 artifact 须原 KMS 密钥或静态密钥恢复 |
| **KMS** | CMK 策略须允许 **Agent 执行主体** **`kms:GenerateDataKey`**（备份）与 **`kms:Decrypt`**（恢复）；审计在 CloudTrail / 等价 |

## 相关文档

- [配置参考](../install/configuration.md)
- [租户模型](../reference/tenants.md)（租户默认 CMK、强制加密）
- [策略与定时](../guides/policies-and-schedules.md)
- [备份与恢复流程](../guides/backup-and-restore.md)
