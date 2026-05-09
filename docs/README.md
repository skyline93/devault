# 文档索引与实现差距

本目录为仓库内 **`docs/`** 的入口说明。详细设计叙述仍以 **[`docs-old/`](../docs-old/)** 为主（历史命名保留）；**对外文档站**源码在 **`website/docs/`**（Docusaurus）。

## 站内链接

| 文档 | 用途 |
|------|------|
| [`docs-old/development-design.md`](../docs-old/development-design.md) | 开发设计、阶段与非目标 |
| [目标架构（文档站）](../website/docs/intro/target-architecture.md) | 边缘 Agent + 控制面：原则、控制/数据面、Pull 序列、存储与安全摘要 |
| [`docs-old/enterprise-backlog.md`](../docs-old/enterprise-backlog.md) | 企业能力待办与验收口径 |
| [`docs/compatibility.json`](compatibility.json) | 控制面 / Agent 兼容矩阵（CI 校验） |
| [`docs/RELEASE.md`](RELEASE.md) | 发版检查清单 |

## 愿景 vs 当前实现（差距表）

以下对照 **`docs-old/README.md`** 等愿景描述，避免销售或交付预期与仓库现状错位。

| 愿景/设计文档中的能力 | 当前实现状态 | 说明与文档 |
|------------------------|--------------|------------|
| PostgreSQL / MySQL / Redis 等**数据库备份插件** | **未实现** | 文件备份 **`file`** 插件为主；路线见 [`website/docs/intro/roadmap.md`](../website/docs/intro/roadmap.md)、企业待办 **M2·九** |
| **增量备份**、WAL/binlog、**PITR** | **未实现** | 全量文件备份 + 对象存储；非目标见 `development-design.md` |
| **Docker 自动发现**（`devault scan` 扫描容器/Compose） | **未实现** | 策略路径需显式配置 |
| **Docker Volume 快照 / 差异备份** | **未实现** | Agent 读允许路径下的文件系统 |
| Web UI **Dashboard**（趋势、存储占用大盘等） | **部分**：简易 Jobs/Artifacts/Policies 等页 | 见 [`website/docs/guides/web-console.md`](../website/docs/guides/web-console.md) |
| **Celery Worker** 执行备份 | **已移除** | 执行单元为 **边缘 Agent**（gRPC 租约 + 直传 S3）；设计文档部分路径描述可能仍写 Celery，以代码为准 |
| **客户自带 Bucket（BYOB）** | **未实现** | 单租户/平台桶前缀模型；见 [目标架构 · 统一存储与后续扩展](../website/docs/intro/target-architecture.md#unified-storage-extensions) |
| **WORM / Object Lock、Legal Hold** | **未实现** | 企业待办 §五 |
| **KMS 信封加密** | **未实现** | 可选 **Artifact 对称密钥**在 Agent 环境变量；见 [`artifact-encryption.md`](../website/docs/security/artifact-encryption.md) |

若你维护 **`docs-old/README.md`** 愿景列表，请与本表同步更新，或在 PR 中引用本文件。
