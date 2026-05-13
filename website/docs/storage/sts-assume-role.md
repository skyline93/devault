---
sidebar_position: 2
title: STS 与 AssumeRole
description: 控制面使用短时会话访问 S3（按存储 profile）
---

# STS 与 AssumeRole（控制面 → S3）

访问密钥可通过 **STS `AssumeRole`** 获取短时凭证，而非长期 AK/SK 固化在库中。连接信息来自 **`devault_storage_profiles`**（平台 **admin** 经 **`/api/v1/storage-profiles`** 维护；静态 AK/SK 以 **`DEVAULT_STORAGE_CONFIG_MASTER_KEY`** Fernet 加密落库）。

## 凭证解析顺序（每条 S3 profile）

对 **`S3ConnSpec`** 构造 boto3 S3 客户端时（AssumeRole 结果带进程内缓存、过期前刷新）：

1. **`s3_assume_role_arn`**（profile 上）已设置 → STS `AssumeRole`；基底为 profile 上的静态密钥（若已配置并解密成功）或**默认凭证链**。
2. 未 AssumeRole，但 profile 有静态密钥对 → 直连。
3. 皆无 → 默认凭证链（IRSA、实例配置、`AWS_*` 环境变量）。

静态 **Access key / Secret key** 在 API 中成对提交；省略则表示不依赖静态密钥（仅用 AssumeRole 或默认链）。

## 进程级 STS 调优（仍来自环境变量）

这些变量作用于 **STS 客户端**与 **AssumeRole 调用参数**，与具体 profile 的 endpoint/region/bucket 无关：

| 变量 | 说明 |
|------|------|
| `DEVAULT_S3_ASSUME_ROLE_SESSION_NAME` | （可选）默认 `devault-control-plane` |
| `DEVAULT_S3_ASSUME_ROLE_DURATION_SECONDS` | （可选）900–43200，默认 `3600` |
| `DEVAULT_S3_STS_REGION` / `DEVAULT_S3_STS_ENDPOINT_URL` / `DEVAULT_S3_STS_USE_SSL` | STS 客户端 |

实现：`src/devault/storage/s3_client.py`（**`build_s3_client_from_spec`**）、`src/devault/services/storage_profiles.py`。

## 首次迁移与 Compose 种子

**`alembic upgrade`** 仅创建 **`devault_storage_profiles`** 表与 **`artifacts.storage_profile_id`**（可空）；**不**再插入默认 profile。运行期控制面从库中 profile 解析 S3；scheduler 与制品读路径一致。

## 典型部署模式

### EKS（IRSA）

服务账号 Web Identity → 基底角色可 `AssumeRole` 到数据面角色 **B**；在 profile 中填 **`s3_assume_role_arn=B`**，不配静态密钥。

### EC2 实例配置文件

同思路两段式或直接桶策略挂载在实例角色。

### Vault 等动态密钥

若进程环境写入 `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_SESSION_TOKEN` 可走凭证链。

### 本地与 MinIO

演示多用 profile 内静态密钥；MinIO STS 能力与 AWS 有差异时需核对端点。

## 与预签名 TTL

`DurationSeconds` 应 **≥** 备份作业所需的预签名有效期（`DEVAULT_PRESIGN_TTL_SECONDS`）。

## 相关文档

- [对象存储模型](./object-store-model.md)  
- [租户与访问控制](../admin/tenants-and-rbac.md)
