---
sidebar_position: 3
title: 大对象与恢复
description: 分片上传、重试与恢复侧行为
---

# 大对象与恢复

## 分片上传（Multipart）

超过阈值时使用 **Multipart** 提高吞吐与可靠性。实现见 `src/devault/storage/` 等模块。

启用 **`encrypt_artifacts`** 时**仅在加密完成后**进入 Multipart WIP；续传前校验 **策略与 manifest 的 encryption 块**以及 **WIP 与 checkpoint 大小**（见 [Artifact 静态加密](../trust/artifact-encryption.md)）。

## 重试

分片失败时实现侧重试（策略以代码为准）。

## 恢复

流式读取与校验以降低峰值磁盘占用；部署前建议在预发对目标数据量抽样验证。

## 相关环境变量

见 [存储调优](./tuning.md)。
