# Change: pgBackRest 一期物理备份（FULL + INCR）

## Why

工程方案 [PostgreSQL pgBackRest 物理备份总体方案（分三期）](../../../website/docs/engineering/postgresql-pgbackrest-physical-backup.md) 已定义 Patroni、S3 repo、Agent 非 DB 机与 DeVault 编排的一期范围，但控制面与 Agent **仅实现 `file` 插件**：备份完成路径强依赖 **bundle/manifest + Artifact**，无法承载 **pgBackRest 独占 S3 repo 布局**。需要在 **不考虑向后兼容** 的前提下，引入 **`postgres_pgbackrest`（或项目内最终定名）** 插件及完整可运行闭环，使每个任务阶段结束时 **测试与主路径均可执行**（API → Job → gRPC 租约 → Agent 子进程 → CompleteJob → 可查询结果）。

## What Changes

- **BREAKING**：备份 Job 成功完成语义按 **plugin 分支**：`file` 保持现有 Artifact + 完整性校验；**物理备份插件** 成功时 **不创建** 传统 `Artifact`（bundle/manifest），改为 **`result_meta`（及/或后续扩展表）** 登记备份点摘要；OpenAPI、控制台与集成测试同步。
- **BREAKING**：`CreateBackupJobBody` / Policy 校验扩展，允许新插件及 **非敏感** 配置 JSON schema；**禁止** 数据库连接密码等进入 `config_snapshot` 明文。
- **新增**：`PluginName`（或等价枚举）与全链路 `plugin` 字符串；控制面 `create_backup_job`、调度器 `fire_scheduled_backup` 与租约队列 **对新插件一致可用**。
- **新增**：边缘 Agent 对 `BACKUP` + 新插件：以 **固定 argv** 调用 `pgbackrest backup`（`full` / `incr`），可选随后 `pgbackrest info --output=json`，经 **`CompleteJob.result_summary_json`**（或约定字段）回传；**不调用** `RequestStorageGrant` 文件上传路径。
- **新增**：`CompleteJob` gRPC 处理逻辑中，对新插件成功路径 **跳过** bundle/manifest/S3 manifest 校验与 `Artifact` 插入；失败路径沿用 `error_code` / `error_message`。
- **新增**：控制台策略与作业列表/详情对新插件的最小可用面；`verify_console_openapi_contract` 与相关单测更新。
- **新增**：Agent 交付镜像或文档中 **pgBackRest 二进制** 与版本矩阵说明；CI 中可测的最小集成（mock 或 testcontainer 择一，以任务清单为准）。
- **新增（演示栈）**：`deploy/docker-compose.yml`（及 `make demo-stack-up` 所用 profile）在启用 Agent 时，**增加或扩展** 服务，使演示环境具备 **① 与元数据库分离的「被备份」PostgreSQL 实例**（供 `pg_host` / `pg_data_path` 指向）、**② 在现有 `deploy/Dockerfile` 中安装 `pgbackrest` CLI（方案 A，定案）**，使 **`agent` / `agent2` 共用镜像** 即具备物理备份执行能力。凭据经 **Agent 环境变量** 注入 pgBackRest 的 S3 repo（与现有 MinIO 对齐）；`demo-stack-init` 或等价脚本 **可选** 幂等创建演示用 `postgres_pgbackrest` 策略与绑定，便于 **一次 FULL**（及文档化的 **expire**）冒烟，无需外部集群。
- **定案**：**同一租户** 下允许 **`file` 与物理备份插件策略并存**（多条 Policy 各带 `plugin`）；租户级不设「二选一」互斥，隔离依赖 **`bound_agent_id` / Agent 池** 与运维规范。
- **定案**：**一期纳入 `pgbackrest expire` 自动化**：通过 **Schedule + Job**（或等价调度入口）周期性入队 **`expire` 运维作业**，由已绑定且安装 pgBackRest 的 Agent 执行固定 argv，完成语义与物理 **`backup`** 一致（**无 Artifact**，摘要进 `result_meta`）。
- **明确非目标（本变更不包含）**：WAL `archive-push`、产品化 `restore`、PITR、将 pgBackRest repo 对象搬进 DeVault 文件 artifact 桶。

## Capabilities

### New Capabilities

- `pgbackrest-physical-backup`：租户侧通过 DeVault 编排 **pgBackRest `backup`（FULL/INCR）**；控制面 API、Policy 配置、gRPC 完成语义、Agent 执行与安全约束（无 `shell=True`）及可观测性要求。

### Modified Capabilities

- （无）当前 `openspec/specs/` 下无既有「作业/备份」能力规范；本变更以 **新增能力** 为主。若后续归档时合并到更大「edge-jobs」能力，可在归档阶段调整。

## Impact

- **后端**：`src/devault/core/enums.py`、`api/schemas.py`、`services/control.py`、`grpc/servicer.py`（`CompleteJob`、`RequestStorageGrant` 分支）、`agent/main.py`、策略校验模块、指标 `JOB_DURATION_SECONDS` 等。
- **数据**：可能需 **Alembic 迁移**（若引入 `Artifact` 扩展字段或独立 `physical_backup_points` 表；若一期仅用 `jobs.result_meta` 则可无迁移或极小迁移）。
- **proto / 生成代码**：仅当选择扩展 `CompleteJobRequest` 而非纯 `result_summary_json` 时需改 `agent.proto` 并再生；设计文档默认 **优先 JSON 载荷** 以减少 proto 变更面。
- **控制台**：`console/` 策略与备份向导、作业详情、`locales`。
- **文档**：工程方案交叉引用、用户/运维说明中 RPO（无 WAL）边界；**演示栈 compose 与附录 A 服务/env 对照表**。
- **演示栈 / 部署**：`deploy/docker-compose.yml`、**`deploy/Dockerfile`（扩展安装 pgBackRest，方案 A）**、`deploy/scripts/bootstrap_demo_stack.py`、`deploy/.env.stack.example`。
- **依赖**：无 Patroni 代码进仓要求。**演示栈** 内应自带「目标 PG + MinIO + pgBackRest Agent」闭环；生产/Patroni 联调仍由运维文档说明。
