## Context

- 现状：`PluginName.FILE`；`create_backup_job` 与 `CompleteJob` 对 `BACKUP` 假设 **DeVault 桶内 bundle + JSON manifest + `Artifact`**（`grpc/servicer.py`）；Agent `_run_one_job` 仅构建 tarball 并走预签名上传（`agent/main.py`）。
- 目标：对齐 [postgresql-pgbackrest-physical-backup.md](../../../website/docs/engineering/postgresql-pgbackrest-physical-backup.md) **一期**：FULL + INCR，`pgbackrest` 写 **独立配置的 S3 repo**（或 NAS repo 路径），与 DeVault 文件 artifact **解耦**。
- 约束：**不要求向后兼容**；每个里程碑合并后仍须 **全量测试通过、主路径可运行**（控制面 + Agent + 最小控制台或 API-only 验收二选一由任务清单收口）。

## Goals / Non-Goals

**Goals:**

- 租户可创建 **物理备份策略**（非敏感配置 + 凭据引用约定），并 **手动或 Schedule** 产生 `BACKUP` Job。
- 具备 **pgBackRest** 与配置的 Agent 可租约执行 **`pgbackrest backup`**（`--type=full|incr`），成功后控制面持久化 **可查询摘要**（`result_meta` +/或扩展表）。
- **CompleteJob** 对新插件 **不** 要求 `bundle_key` / `manifest_key`，**不** 走文件 manifest 校验逻辑。
- 控制台与 OpenAPI 契约 **最小可用**；CI **绿**。
- **同一租户** 可同时持有 **`file` 与 `postgres_pgbackrest` 策略**（及多条同插件策略）；控制面 **不对租户施加「仅允许一种备份插件」限制**。
- **一期** 支持 **`pgbackrest expire` 自动化 Job**（见决策 8），与 `backup` 共用插件与租约完成路径差异仅在子命令与校验字段。

**Non-Goals:**

- WAL 归档、`restore` 产品化、PITR、跨租户 repo 浏览、将 pgBackRest 内部对象列表产品化暴露。

## Decisions

1. **插件标识**  
   - 采用 `postgres_pgbackrest`（或实现期统一为小写 `postgres_pgbackrest`，与 `jobs.plugin` / `policies.plugin` 一致）。  
   - **备选**：`pgbackrest` 单名；若选须在 OpenAPI 与枚举一处定稿。

2. **成功完成的数据落点（一期）**  
   - **默认**：成功备份的结构化结果写入 **`jobs.result_meta`**（及 `CompleteJobRequest.result_summary_json` 同源 JSON），字段包含但不限于：`stanza`、`backup_type`、`backup_label`（若可得）、`pgbackrest_info`（解析后的对象或原始 JSON 字符串）、`finished_at` 冗余可选。  
   - **不创建** `artifacts` 行（避免伪造 `bundle_key`）。  
   - **备选**：新建表 `physical_backup_points`；若引入须在 tasks 中单独立项迁移与 API 列表。

3. **凭据与配置**  
   - `config_snapshot` 含：`pgbackrest_operation`：`backup` | `expire`（**缺省 `backup`**）；当为 `backup` 时再要求 **`backup_type`**（或等价字段）：`full` | `incr`。当为 `expire` 时 **不要求** `backup_type`。  
   - 另含：`stanza`、`pg_host`、`pg_port`、`pg_data_path`、repo 非密钥描述等。  
   - 连接密码、`AWS_SECRET_ACCESS_KEY` 等：**仅允许** Agent 进程环境、挂载 Secret 或 **控制面不落库的 secret_ref 键名**（由 Agent 侧 resolver 解析）；控制面校验 **禁止** 明文密码字段出现在持久化 JSON。

4. **gRPC 与 proto**  
   - **一期优先**：不扩展 proto，使用现有 **`result_summary_json`** 传递摘要；`CompleteJob` 成功分支按 `job.plugin` 分流。  
   - 若 `result_summary_json` 长度或结构化不足，再增量扩展 proto（单独 PR 仍须保持可运行）。

5. **Agent 执行**  
   - `subprocess` 固定参数列表；超时时间与 `job_lease_ttl_seconds` 协调，必要时 **租约续期**（`ReportProgress` + 控制面延长 `lease_expires_at`）或阶段性文档化「一期仅支持小于 TTL 的备份窗口」。  
   - `pgbackrest.conf`：由 Agent 根据 Job config + 挂载模板 **渲染临时文件**，进程级 `PGPASSFILE` 等按安全规范。

6. **租约与 Agent 选择**  
   - **一期最小**：依赖现有 **`Policy.bound_agent_id`**（或项目已有 agent pool 绑定）将物理备份 Job **限制到已安装 pgBackRest 的 Agent**；`_pending_candidate_ids` 暂不按 capability 过滤时，**文档 + 默认策略** 要求绑定。  
   - **增强（可选任务）**：Register / Heartbeat 上报 **`server_capabilities`** 风格 capability（如 `pgbackrest`），控制面租约时过滤。

7. **指标与计费**  
   - `JOB_DURATION_SECONDS` 等 **按真实 `job.plugin` label**，不得写死 `file`。  
   - `BILLING_COMMITTED_BYTES_TOTAL`：物理备份一期 **可不 increment** 或 increment `0`，在 tasks 中明确产品决策并加注释。

8. **同租户多插件与 expire 作业形状**  
   - **并存**：不在租户表或 API 层禁止 `file` + `postgres_pgbackrest` 多条 `policies`；冲突避免靠 **不同 Policy 绑定不同 Agent** 及文档。  
   - **`expire`**：在物理备份 Policy 的 `config`（或 Job 快照）中增加 **`pgbackrest_operation`**（或同名）枚举：`backup` | `expire`（缺省 `backup`）。  
     - **调度**：`fire_scheduled_backup` 对绑定到 **物理备份策略** 的 `Schedule` 与 **备份策略** 使用 **同一入队路径**：每触发一次即创建 `kind=backup`、`plugin=postgres_pgbackrest` 的 Job，`config_snapshot` **完整拷贝** `policy.config`（含 `pgbackrest_operation`）；**备份类策略** 与 **仅 expire 类策略** 可为 **两条 Policy + 各自 Schedule**（推荐），由 Agent 根据 `pgbackrest_operation` 执行 `pgbackrest backup` 或 `pgbackrest expire`。**备选**：新增 `JobKind`（如 `maintenance`）——若引入须同步 OpenAPI/控制台；默认采用 **同 kind 不同 operation** 以减少表与租约分叉。

9. **演示栈：含 pgBackRest 的 Agent 镜像（定案）**  
   - **方案 A**：仅在 **`deploy/Dockerfile`** 中安装 **pgbackrest**；`agent`、`agent2` 与 **api / scheduler** 共用该构建产出的镜像（体积略增可接受）。  
   - **不采用** 方案 B（独立 `Dockerfile.agent-pgbackrest` 或第三 `agent-pgbr` 服务）作为仓库默认演示路径；若未来需「极瘦」生产 Agent 镜像，可另开变更将 pgBackRest 拆为 profile 构建。

## Risks / Trade-offs

- **INCR 无前置 FULL**：链失败 → 调度层或产品层需 **FULL 先行** 策略（文档 + 可选校验任务）。  
- **长备份超过租约**：失败或误杀 → 通过 TTL 调优、续租或文档限制缓解。  
- **无 Artifact**：现有「制品列表」页面可能为空 → 控制台需 **作业维度展示 result_meta**，避免用户误以为未备份。

## Migration Plan

- **不考虑向后兼容**：允许一次性重命名枚举、调整 OpenAPI；不强制数据回填。  
- 部署顺序：先控制面（接受新 plugin 与 CompleteJob 分支）→ 再发 Agent 镜像（避免旧 Agent 领到新 Job 后无法执行）。

## Open Questions

- （已闭合）同租户 **file + pgbackrest 并存**、`expire` **一期自动化** 已写入决策 8 与 proposal。  
- **expire 与 FULL 调度顺序**：是否强制 **先 backup 后 expire** 的 cron 间隔由运维配置；产品层可选告警「expire 过于频繁」。

## Demo stack（compose / `make demo-stack-up`）

**目标**：在仓库自带演示栈中 **无需外部 Patroni/PG** 即可完成 pgBackRest 一期冒烟：**Agent 执行 `backup`/`expire` → `CompleteJob` → `result_meta`**。

1. **被备份 PostgreSQL（独立服务）**  
   - **不得** 与控制面元数据库 `postgres`（`devault` 库）混为同一「备份目标」叙事：新增专用服务（建议名如 `postgres-pgbr-demo`），镜像与版本在 `tasks` 中定稿（如 `postgres:14` 与元数据库一致便于缓存）。  
   - 暴露 **仅 compose 内网** 或可选 host 端口；`pg_host` 使用 **Docker DNS 服务名**，`pg_port` 默认 `5432`，`pg_data_path` 与官方镜像数据目录一致（如 `/var/lib/postgresql/data`）。  
   - **演示级** 认证：`pg_hba` / 角色以「能跑通一次 FULL」为底线（例如专用备份角色 + 口令经 **Agent 环境变量** 注入，**不** 写入 Policy JSON）；若采用 `trust` 仅限 compose 内网须在注释中标明 **禁止生产照抄**。

2. **带 pgBackRest 的 Agent（定案：方案 A）**  
   - 在 **`deploy/Dockerfile`** 中通过 `apt-get install`（或 `python:3.12-slim` 发行版等价方式）安装 **pgbackrest** 及其运行时依赖，使 **`agent` 与 `agent2` 与 API scheduler 共用同一构建上下文产出的镜像** 均含 CLI；**不** 引入单独的 `Dockerfile.agent-pgbr` 或第三 Agent 服务作为演示栈默认路径。  
   - 与 **Debian bookworm** 仓库中 pgBackRest 与 **PostgreSQL 客户端大版本** 的匹配关系在实现 PR 中说明；若包版本落后于目标 PG 小版本，以「能完成 stanza 首次 `backup --type=full`」为演示验收底线。  
   - Agent 容器需能 **TCP 访问** `postgres-pgbr-demo:5432`，并能访问 **MinIO**（与现有 `DEVAULT_S3_ENDPOINT` 同网段逻辑；pgBackRest 使用 **`PGBACKREST_REPO1_S3_*`** 等环境变量，与 `policy.config` 中非敏感字段一致）。

3. **Repo 与 stanza**  
   - MinIO bucket 可与现有 `DEVAULT_S3_BUCKET` 共用或 **独立 prefix**（如 `pgbr-demo/`），避免与 file artifact 对象键冲突；在 `design`/`附录` 写明 **repo1-path-prefix** 与 DeVault artifact 前缀边界。  
   - `stanza` 名在演示栈中 **固定常量**（如 `demo`），与 `pgbackrest.conf` / `bootstrap` 若创建 stanza 的步骤一致。

4. **bootstrap 与文档**  
   - `deploy/scripts/bootstrap_demo_stack.py`（或独立 `bootstrap_pgbr_demo.py`）在 **`DEMO_STACK_PGBACKREST_ENABLED=true`**（或等价开关）时：创建 `postgres_pgbackrest` Policy + `bound_agent_id` 指向 **含 pgBackRest 的 Agent**；**不** 在 API 持久化中写入 S3 secret。  
   - `website/docs/engineering/postgresql-pgbackrest-physical-backup.md` 附录 A 增加 **「compose 服务名对照表」** 与 **环境变量清单**。

5. **与现有双 Agent 关系**  
   - **`agent` 与 `agent2` 镜像一致**：均含 pgBackRest；**file** 与 **postgres_pgbackrest** 策略通过 **`bound_agent_id`** 区分执行体。物理备份策略应绑到 **能访问 `postgres-pgbr-demo` 且已配置 `PGBACKREST_*` 环境变量** 的实例；file 策略可继续绑任意具备路径与预签上传能力的 Agent。文档中给出 **默认绑定矩阵**（例如 `agent` → file demo，`agent2` → pgbr demo，可互换但须同时满足路径与网络）。
