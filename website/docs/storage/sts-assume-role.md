---
sidebar_position: 2
title: STS 与 AssumeRole（控制面 → S3）
description: 使用短时会话密钥访问 S3，避免在镜像或 ConfigMap 中长期存放静态 AK/SK
---

# STS 与 AssumeRole（控制面 → S3）

当 `DEVAULT_STORAGE_BACKEND=s3` 时，控制面需要调用 S3 API 完成：`CreateMultipartUpload` / `CompleteMultipartUpload` / `ListParts` / `AbortMultipartUpload` / `HeadObject` 等，以及为 Agent 签发 **预签名 URL**。自本功能起，访问密钥可通过 **STS `AssumeRole`** 获取的 **短时** `AccessKeyId` / `SecretAccessKey` / `SessionToken` 提供，而不必在 Kubernetes Secret 或镜像中固化长期 IAM 用户密钥。

## 凭证解析顺序

控制面在每次需要 boto3 S3 客户端时（实现上会合并逻辑；AssumeRole 路径带**内存缓存**，在过期前约 5 分钟刷新）按以下顺序解析：

1. **已设置 `DEVAULT_S3_ASSUME_ROLE_ARN`**  
   - 使用 **STS** 调用 `AssumeRole`。  
   - **基底凭证**：若同时配置了 `DEVAULT_S3_ACCESS_KEY` 与 `DEVAULT_S3_SECRET_KEY`，则以其作为调用 STS 的身份；若两者皆未配置，则使用 **进程默认凭证链**（见下文）。  
   - 使用返回的 **临时密钥** 构造 S3 客户端（与预签名、Multipart 控制面 API 一致）。

2. **未配置 AssumeRole，但配置了静态密钥对**  
   - 与历史行为一致，直接使用 `DEVAULT_S3_ACCESS_KEY` / `DEVAULT_S3_SECRET_KEY`。

3. **两者皆无（无静态密钥、无角色 ARN）**  
   - 使用 boto3 **默认凭证链** 创建 S3 客户端（适用于 **EKS IRSA**、**EC2 实例配置文件**、环境变量 `AWS_ACCESS_KEY_ID` 等）。若链上无可用凭证，将在运行时由 boto3 报错。

`DEVAULT_S3_ACCESS_KEY` / `DEVAULT_S3_SECRET_KEY` 必须 **成对出现或成对省略**；单独设置其一会在启动配置校验阶段失败。

## 环境变量一览

| 变量 | 说明 |
|------|------|
| `DEVAULT_S3_ASSUME_ROLE_ARN` | 要承担的目标角色 ARN；设置后走 STS 路径 |
| `DEVAULT_S3_ASSUME_ROLE_EXTERNAL_ID` | （可选）跨账户信任时的 `ExternalId` |
| `DEVAULT_S3_ASSUME_ROLE_SESSION_NAME` | （可选）`RoleSessionName`，默认 `devault-control-plane`，最长 64 字符 |
| `DEVAULT_S3_ASSUME_ROLE_DURATION_SECONDS` | （可选）`DurationSeconds`，默认 `3600`，允许范围 **900–43200**（以角色与账号策略为准） |
| `DEVAULT_S3_STS_REGION` | （可选）STS 客户端区域；未设置时使用 `DEVAULT_S3_REGION` |
| `DEVAULT_S3_STS_ENDPOINT_URL` | （可选）自定义 STS 端点（如 LocalStack）；留空则使用 AWS 区域 STS |
| `DEVAULT_S3_STS_USE_SSL` | （可选）STS 客户端是否 TLS，默认 `true`；仅在使用 `http://` 类 STS 端点的实验环境设为 `false` |

其余 `DEVAULT_S3_ENDPOINT`、`DEVAULT_S3_BUCKET`、`DEVAULT_S3_REGION`、`DEVAULT_S3_USE_SSL` 等仍作用于 **S3** 客户端本身（与 MinIO / 自建网关兼容）。

**按租户覆盖（BYOB）**：若某 **`tenants`** 行设置了 **`s3_assume_role_arn`**，则对该租户 artifact 的 **预签名、Multipart 控制 API、Head/Get 存在性检查、scheduler 删除** 均 **优先** 使用该 ARN（及可选 **`s3_assume_role_external_id`**）调用 STS，而**不是** `DEVAULT_S3_ASSUME_ROLE_ARN`。全局静态密钥对仍可作为 **AssumeRole 的基底身份**（与上表第 1 步一致）。桶名由 **`tenants.s3_bucket`** 或回退 **`DEVAULT_S3_BUCKET`** 决定，见 [租户模型](../reference/tenants.md)。

## 典型部署模式

### Amazon EKS（IRSA）

1. 为控制面 ServiceAccount 绑定 **OIDC 联合** 角色 **A**（仅能 `sts:AssumeRole` 到数据面角色 **B**，或直接附加 S3 策略；若采用本节的 **AssumeRole 到 B** 模式，则 A 的权限可收紧为仅 `sts:AssumeRole` 到 B）。  
2. 角色 **B** 持有目标桶的 `s3:*`（或最小化）策略。  
3. 配置 `DEVAULT_S3_ASSUME_ROLE_ARN` 为角色 **B** 的 ARN，**不**设置静态 `DEVAULT_S3_ACCESS_KEY` / `DEVAULT_S3_SECRET_KEY`，使基底身份来自 Pod 的 Web Identity。  
4. 将 `DEVAULT_S3_REGION`、`DEVAULT_S3_BUCKET` 等与桶一致；S3 端点留空以使用 AWS 默认。

### EC2 实例配置文件

将实例配置文件角色配置为可 `sts:AssumeRole` 到专用 S3 角色，或直接在实例角色上挂载桶策略；若采用「实例角色 → AssumeRole 到专用角色」两段式，与 IRSA 类似填写 `DEVAULT_S3_ASSUME_ROLE_ARN`。

### HashiCorp Vault 等动态密钥

常见做法是由 Sidecar 或 init 容器将短期密钥写入 **环境变量** 或 **共享卷**；若暴露为 `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_SESSION_TOKEN`，可不配置 `DEVAULT_S3_*` 静态密钥，也不配置 `DEVAULT_S3_ASSUME_ROLE_ARN`，走 **默认凭证链**（第 3 条）。若仍希望 **显式** 经 Vault 签发的长期用户密钥去 AssumeRole，则只配 `DEVAULT_S3_ACCESS_KEY` / `DEVAULT_S3_SECRET_KEY` + `DEVAULT_S3_ASSUME_ROLE_ARN`。

### 本地与 MinIO

演示栈继续使用 `DEVAULT_S3_ACCESS_KEY` / `DEVAULT_S3_SECRET_KEY` 即可。MinIO 对 STS `AssumeRole` 的支持与 AWS 存在差异，生产若用 MinIO 自建 STS，需自行核对 **端点、签名版本与策略**；可通过 `DEVAULT_S3_STS_ENDPOINT_URL` 指向 STS 服务。

## 与预签名 TTL

AssumeRole 的 `DurationSeconds` 应 **不小于** 备份作业中预签名 URL 所需的有效期（见 `DEVAULT_PRESIGN_TTL_SECONDS`），否则在租约较长时可能出现 **控制面 S3 API 成功而后续同一进程内凭证过期** 的边缘情况。默认 3600 秒与默认预签名 TTL 对齐；若提高预签名 TTL，请同步提高角色会话时长（在 IAM 允许范围内）。

## 实现位置

- 凭证解析与缓存：`src/devault/storage/s3_client.py`  
- 配置模型：`src/devault/settings.py`  
- 企业待办清单见仓库内 `docs-old/enterprise-backlog.md`（**M1 · 二**）；数据面说明见 `docs-old/s3-data-plane.md`。
