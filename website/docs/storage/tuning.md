---
sidebar_position: 3
title: 存储调优
description: 阈值类环境变量与调优建议
---

# 存储调优

以下变量用于控制分片与恢复行为（名称以仓库内设置类为准，若有增减以代码为准）。

| 变量 | 作用 |
|------|------|
| `DEVAULT_S3_MULTIPART_THRESHOLD_BYTES` | 超过该大小时启用 multipart 上传路径 |
| `DEVAULT_S3_MULTIPART_PART_SIZE_BYTES` | 分片大小 |
| `DEVAULT_AGENT_MULTIPART_STATE_DIR` | Agent：大备份的续传目录根（默认 `~/.cache/devault-agent`；其下 `multipart/<job_id>/` 存 `bundle.tar.gz` 与 `checkpoint.json`） |

## 调优建议

- **高带宽、低延迟**：可适当增大分片大小，减少请求次数。
- **弱网或小对象居多**：降低阈值或分片大小需权衡请求开销与失败重试粒度。
- **Agent 重启续传**：续传依赖同一 **job id** 与磁盘上的 WIP 目录；容器场景请将 **`DEVAULT_AGENT_MULTIPART_STATE_DIR`** 挂载到持久卷，否则重启会丢失本地 bundle。
- 变更后应对接同一 S3 端点做**实际上传/恢复压测**，观察 5xx、超时与 Prometheus 指标。
