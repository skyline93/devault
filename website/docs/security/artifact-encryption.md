---
sidebar_position: 4
title: Artifact 静态加密（AES-GCM）
description: 策略级可选加密、密钥配置与 manifest 字段
---

# Artifact 静态加密（AES-GCM）

对象存储中的 **bundle** 可在上传前由 Agent 使用 **AES-256-GCM** 加密；控制面 **不落明文密钥**，仅在 `CompleteJob` 时读取 **manifest** 校验校验和并设置 **`artifacts.encrypted`**。

## 启用方式

1. **策略配置**：在文件备份策略（HTTP API / UI）将 **`encrypt_artifacts`** 设为 `true`（默认 `false`）。
2. **Agent 环境变量**：设置 **`DEVAULT_ARTIFACT_ENCRYPTION_KEY`** 为标准 Base64 编码的 **32 字节** AES-256 密钥（与同一密钥用于解密恢复）。
3. **运行备份**：Agent 在生成 `tar.gz` 后按 **`devault-chunked-v1`** 格式分层加密（默认每块最大 64MiB 明文），再上传密文；manifest 记录密文校验和与 **`plaintext_checksum_sha256`**（内层 tarball）。

恢复时控制面在 **`RequestStorageGrant`（READ）** 为 bundle 与 **manifest** 分别签发预签名 GET；Agent 拉取 manifest 判断是否存在 **`encryption`** 字段，必要时解密后再解压。

## Manifest 与数据库

- **`manifest.json`**：`encryption` 对象含 `algorithm`、`format`（`devault-chunked-v1`）、`chunk_size_bytes`、`aad`。
- **`artifacts.encrypted`**：由控制面根据 manifest 写入；与 **`checksum_sha256`**（密文 SHA-256）一致。

## 密钥治理（运维）

| 主题 | 说明 |
|------|------|
| **生成** | `openssl rand -base64 32`（或 KMS / HSM 导出后 Base64） |
| **轮换** | 新密钥仅影响**新**备份；旧 artifact 仍须原密钥恢复 |
| **KMS / CMK** | 当前版本由运维将 **数据密钥** 注入 Agent；云上可将密钥来自 Secrets Manager / Vault，与本字段等价 |

更通用的信封加密（按租户 DEK、按作业封装）可作为后续增强；本节对应企业待办 **「Artifact 加密」** 的可运行基线。

## 相关文档

- [配置参考](../install/configuration.md) · Agent 段 `DEVAULT_ARTIFACT_ENCRYPTION_KEY`
- [备份与恢复流程](../guides/backup-and-restore.md)
