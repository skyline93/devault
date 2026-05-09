---
sidebar_position: 2
title: 大对象与恢复
description: 分片上传、重试与恢复侧行为
---

# 大对象与恢复

## 分片上传（Multipart）

超过阈值时，备份路径可使用 **Multipart** 分片上传，以提高大文件可靠性与吞吐。实现细节见 `src/devault/storage/` 下相关模块；与 **Agent 本地续传 checkpoint**、**S3 `ListParts` 补签** 的完整叙述见仓库 `docs-old/s3-data-plane.md` §3。

启用 **`encrypt_artifacts`** 时，**仅在加密完成后** 才进入 Multipart WIP；续传前会校验 **策略与 manifest 的 encryption 块一致** 以及 **WIP 文件大小与 checkpoint**，不匹配则丢弃本地状态并重建（见 [Artifact 静态加密](../security/artifact-encryption.md)）。

## 重试

分片或网络错误时，实现侧可对失败分片进行重试（具体策略以当前代码为准）。

## 恢复

恢复路径可能包含**流式读取与校验**，以降低磁盘峰值占用并尽早发现损坏。行为与校验强度随版本迭代，部署前建议在预发环境对目标数据量做抽样验证。

## 相关环境变量

见 [存储调优](./tuning.md) 中的阈值类变量。
