# 文档索引与实现差距

本目录为仓库内 **`docs/`** 的入口说明。详细设计叙述仍以 **[`docs-old/`](../docs-old/)** 为主（历史命名保留）；**对外文档站**源码在 **`website/docs/`**（Docusaurus）。

## 站内链接

| 文档 | 用途 |
|------|------|
| [`docs-old/development-design.md`](../docs-old/development-design.md) | 开发设计、阶段与非目标 |
| [平台实现架构（文档站）](../website/docs/engineering/platform-architecture.md) | 边缘 Agent + 控制面：原则、控制/数据面、Pull 序列、存储与安全摘要 |
| [`docs-old/enterprise-backlog.md`](../docs-old/enterprise-backlog.md) | 企业能力待办与验收口径（活跃索引） |
| [`docs-old/enterprise-backlog-completed-archive.md`](../docs-old/enterprise-backlog-completed-archive.md) | 企业待办 **Part 1**：索引 **`[x]`**；**Part 2**：已闭合分节正文、§十三、§十二 历史修订、Epic 长说明 |
| [`docs/compatibility.json`](compatibility.json) | 控制面 / Agent 兼容矩阵（CI 校验） |
| [`docs/RELEASE.md`](RELEASE.md) | 发版检查清单 |
| [`docs/iam-service-design.md`](iam-service-design.md) | **独立 IAM 服务** 设计方案（人 + 控制面 API Key）；代码在仓库 **`iam/`** 目录 |
| [`docs/iam-tenant-lifecycle-and-bootstrap.md`](iam-tenant-lifecycle-and-bootstrap.md) | **租户生命周期与引导**：无默认租户、平台管理员（`is_platform_admin` + 零 membership）、关闭自助注册、**独立 CLI** bootstrap、演示栈 **API 初始化**（与主业务隔离） |
| [`docs/web-console-i18n.md`](web-console-i18n.md) | **Web 控制台国际化**：默认英文、可切换简体中文、可扩展语言、Ant Design 生态优先、用户向文案禁止内部术语 |
| [`iam/docs/BACKLOG.md`](../iam/docs/BACKLOG.md) | IAM **按优先级的实现待办**（P0–P5，对齐 `iam-service-design` 与 `docs-old/iam.md`） |

## 愿景 vs 当前实现（差距表）

以下对照 **`docs-old/README.md`** 等愿景描述，避免销售或交付预期与仓库现状错位。

| 愿景/设计文档中的能力 | 当前实现状态 | 说明与文档 |
|------------------------|--------------|------------|
| PostgreSQL / MySQL / Redis 等**数据库备份插件** | **未实现** | 文件备份 **`file`** 插件为主；路线见 [`website/docs/product/roadmap.md`](../website/docs/product/roadmap.md)、企业待办 **M2·九** |
| **增量备份**、WAL/binlog、**PITR** | **未实现** | 全量文件备份 + 对象存储；非目标见 `development-design.md` |
| **Docker 自动发现**（`devault scan` 扫描容器/Compose） | **未实现** | 策略路径需显式配置 |
| **Docker Volume 快照 / 差异备份** | **未实现** | Agent 读允许路径下的文件系统 |
| Web UI **Dashboard**（趋势、存储占用大盘等） | **部分**：Jobs/Artifacts/Policies 等页 | 见 [`website/docs/user/web-console.md`](../website/docs/user/web-console.md) |
| **Celery Worker** 执行备份 | **已移除** | 执行单元为 **边缘 Agent**（gRPC 租约 + 直传 S3）；设计文档部分路径描述可能仍写 Celery，以代码为准 |
| **客户自带 Bucket（BYOB）** | **已实现** | 租户级桶与 AssumeRole；见 [租户与访问控制](../website/docs/admin/tenants-and-rbac.md) |
| **WORM / Object Lock、Legal Hold** | **部分**：Legal Hold 与 Object Lock 策略字段 **已实现**（桶须启用 Object Lock） | 见 [`website/docs/user/policies-and-schedules.md`](../website/docs/user/policies-and-schedules.md)、[`website/docs/trust/artifact-encryption.md`](../website/docs/trust/artifact-encryption.md) |
| **KMS 信封加密** | **已实现**（可选） | 静态 DEK 或 KMS 信封；见 [`website/docs/trust/artifact-encryption.md`](../website/docs/trust/artifact-encryption.md) |

若你维护 **`docs-old/README.md`** 愿景列表，请与本表同步更新，或在 PR 中引用本文件。
