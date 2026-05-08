---
sidebar_position: 1
title: 对象存储模型
description: 预签名、直传与桶生命周期约定
---

# 对象存储模型

## 预签名与直传

当 `DEVAULT_STORAGE_BACKEND=s3` 时，控制面为 Agent 生成 **预签名 URL**，Agent **直接**与 S3 兼容存储通信上传/下载备份对象，减轻控制面带宽压力。

## 桶须事先存在

应用**不会在运行时调用 `CreateBucket`**，以便：

- IAM 权限收敛到对象读写，无需创建桶权限
- 由 Terraform / 运维在部署前创建与 `DEVAULT_S3_BUCKET` 一致的桶

Docker Compose 通过 **`minio-init`** 一次性服务在 MinIO 就绪后执行 `mc mb --ignore-existing`，随后 **`api` / `agent`** 依赖其成功退出再启动，避免首次 PUT 时桶不存在。

## 密钥与端点

`DEVAULT_S3_*` 环境变量需与对象存储实际部署一致；跨区域复制、生命周期策略等在存储侧配置，不由 DeVault 替代。
