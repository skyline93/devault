---
sidebar_position: 2
title: STS 与 AssumeRole
description: 控制面使用短时会话访问 S3
---

# STS 与 AssumeRole（控制面 → S3）

访问密钥可通过 **STS `AssumeRole`** 获取短时凭证，而非长期 AK/SK 固化在 Secret 中。

## 凭证解析顺序

每次构造 boto3 S3 客户端（AssumeRole 结果带内存缓存、过期前刷新）：

1. **`DEVAULT_S3_ASSUME_ROLE_ARN`** 已设置 → STS `AssumeRole`；基底为静态 `DEVAULT_S3_ACCESS_KEY`/`SECRET` 或**默认凭证链**。
2. 未 AssumeRole，但有静态密钥对 → 直连。
3. 皆无 → 默认凭证链（IRSA、实例配置、`AWS_*` 环境变量）。

`DEVAULT_S3_ACCESS_KEY` / `DEVAULT_S3_SECRET_KEY` 须成对出现或成对省略。

## 环境变量一览

| 变量 | 说明 |
|------|------|
| `DEVAULT_S3_ASSUME_ROLE_ARN` | 目标角色 ARN |
| `DEVAULT_S3_ASSUME_ROLE_EXTERNAL_ID` | （可选）ExternalId |
| `DEVAULT_S3_ASSUME_ROLE_SESSION_NAME` | （可选）默认 `devault-control-plane` |
| `DEVAULT_S3_ASSUME_ROLE_DURATION_SECONDS` | （可选）900–43200，默认 `3600` |
| `DEVAULT_S3_STS_REGION` / `DEVAULT_S3_STS_ENDPOINT_URL` / `DEVAULT_S3_STS_USE_SSL` | STS 客户端 |

其余 `DEVAULT_S3_*` 作用于 S3 客户端本身。

**按租户**：若 **`tenants.s3_assume_role_arn`** 已设置，该租户artifact 的预签名 / Multipart / 删除**优先**使用该 ARN（可选 ExternalId）；桶名为 **`tenants.s3_bucket`** 或全局默认。详见 [租户与访问控制](../admin/tenants-and-rbac.md)。

## 典型部署模式

### EKS（IRSA）

服务账号 Web Identity → 基底角色可 `AssumeRole` 到数据面角色 **B**，`DEVAULT_S3_ASSUME_ROLE_ARN=B`，不配静态密钥。

### EC2 实例配置文件

同思路两段式或直接桶策略挂载在实例角色。

### Vault 等动态密钥

若写入 `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_SESSION_TOKEN` 可走凭证链第三条。

### 本地与 MinIO

演示多用静态密钥；MinIO STS 能力与 AWS 有差异时需核对端点。

## 与预签名 TTL

`DurationSeconds` 应 **≥** 备份作业所需的预签名有效期（`DEVAULT_PRESIGN_TTL_SECONDS`）。

## 实现位置

`src/devault/storage/s3_client.py`、`src/devault/settings.py`。
