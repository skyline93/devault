---
sidebar_position: 4
title: 存储调优
description: 阈值类环境变量与调优建议
---

# 存储调优

| 变量 | 作用 |
|------|------|
| `DEVAULT_S3_MULTIPART_THRESHOLD_BYTES` | 超过该大小启用 multipart |
| `DEVAULT_S3_MULTIPART_PART_SIZE_BYTES` | 分片大小 |
| `DEVAULT_AGENT_MULTIPART_STATE_DIR` | Agent 续传目录根（默认 `~/.cache/devault-agent`） |

## 调优建议

- **高带宽低延迟**：适度增大分片减少请求次数。
- **弱网 / 小对象多**：权衡分片大小与重试粒度。
- **Agent 重启续传**：容器须持久化 **`DEVAULT_AGENT_MULTIPART_STATE_DIR`**。
- 变更后做实际上传/恢复压测并结合 Prometheus。
