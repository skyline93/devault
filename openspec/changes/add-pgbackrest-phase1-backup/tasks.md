## 1. 契约与枚举

- [x] 1.1 在 `PluginName`（或项目等价位置）增加物理备份插件常量，并与 `policies.plugin` / `jobs.plugin` 字符串一致
- [x] 1.2 新增 Pydantic 模型 `PgbackrestPhysicalBackupConfigV1`（名称可微调），含 `pgbackrest_operation`（`backup`|`expire`，默认 `backup`）、`stanza`、`pg_host`、`pg_port`、`pg_data_path`、repo 非敏感字段；当 `operation=backup` 时 **必须** 含 `full`|`incr` 备份模式；`expire` 时不得强制备份模式；实现 **禁止明文密钥** 的 `field_validator` / 拒绝列表
- [x] 1.3 扩展 `CreateBackupJobBody` 与 Policy 相关 schema；更新 OpenAPI 导出与 `scripts/verify_console_openapi_contract.py` 所需断言

## 2. 控制面：创建 Job 与校验

- [x] 2.1 在 `services/control.py`（及路由层）实现 `create_backup_job` 对新插件分支：校验租户、policy plugin、内联 config
- [x] 2.2 确保 `fire_scheduled_backup` 对新 `plugin` 写入的 `config_snapshot` 与 file 路径一致且无多余假设
- [x] 2.3 单元测试：合法 config、非法含密码字段、缺必填字段

## 3. gRPC：租约配置与 CompleteJob

- [x] 3.1 `_lease_config_json` 为物理备份 Job 附加必要非敏感字段（含已有 `tenant_id`）；不注入密钥
- [x] 3.2 `CompleteJob`：`BACKUP` + 新插件成功分支 **跳过** bundle/manifest/S3 manifest/`Artifact`；解析 `result_summary_json` 写入 `job.result_meta`；失败分支保持 `error_code`/`error_message`
- [x] 3.3 `CompleteJob`：`BACKUP` + 新插件对缺失/非法 `result_summary_json` 返回 **INVALID_ARGUMENT** 或 **FAILED_PRECONDITION**（与 design 一致）
- [x] 3.4 `RequestStorageGrant`：`BACKUP` + 新插件 **拒绝** 或 **明确失败** 文件 WRITE 意图，避免误走文件预签名路径
- [x] 3.5 单测或 grpc 测试：mock CompleteJob 成功/失败路径

## 4. 边缘 Agent

- [x] 4.1 `agent/main.py`：`BACKUP` 按 `lease.plugin` 分发；新分支调用 **封装模块**（如 `devault/plugins/pgbackrest/runner.py`）执行 `pgbackrest`
- [x] 4.2 使用 `subprocess` 固定 argv；配置临时 `pgbackrest.conf`；超时与日志策略
- [x] 4.3 成功后执行 `pgbackrest info --output=json`（失败则仅记录警告并仍尽力 CompleteJob）
- [x] 4.4 Agent 镜像或 `deploy/` 文档：安装 pgBackRest、依赖与版本说明；本地 `make` / compose 可启动验证路径在 tasks 验收节写明

## 5. 指标与计费

- [x] 5.1 修正 `JOB_DURATION_SECONDS`（及同类写死 `file` label 处）使用 **实际** `job.plugin`
- [x] 5.2 明确 `BILLING_COMMITTED_BYTES_TOTAL` 对物理备份行为（跳过或 0）并加代码注释

## 6. 控制台

- [x] 6.1 策略编辑：新插件表单 Tab 或独立区块；`zh-CN` / `en-US` 文案
- [x] 6.2 备份发起向导或 API 对齐：可选 `plugin` + 校验
- [x] 6.3 作业详情：`result_meta` JSON 展示；**不** 提供基于 `artifacts` 的下载入口给该 plugin
- [x] 6.4 `npm run typecheck` 与 `npm run build` 通过

## 7. 绑定与文档（最小防呆）

- [x] 7.1 文档与控制台提示：物理备份策略 **应** 设置 `bound_agent_id`（或 pool）指向已安装 pgBackRest 的 Agent；**同一租户** 可同时持有 `file` 与物理备份策略，靠 **不同 Policy 绑定不同 Agent** 避免误领；租约队列不按 capability 过滤时的风险说明
- [x] 7.2 （可选）Register/Heartbeat capability `pgbackrest` + 租约过滤——若未做，在 `design.md` Open Questions 留痕并在用户文档写明

## 8. 同租户并存与 expire 自动化

- [x] 8.1 在策略校验与文档中明确：**同一租户** 可同时存在 `file` 与 `postgres_pgbackrest` 策略；API **不** 增加「每租户单插件」互斥校验
- [x] 8.2 确认 `fire_scheduled_backup` 对物理策略 **原样拷贝** `policy.config` 至 `config_snapshot`（含 `pgbackrest_operation=expire`），支持 **仅 expire 的 Policy + Schedule** 入队
- [x] 8.3 Agent：依 `pgbackrest_operation` 调用 `pgbackrest expire` 或 `pgbackrest backup`；日志与 `result_summary_json` 区分 `operation`
- [x] 8.4 `CompleteJob` 校验：`expire` 成功完成时 **同样** 不要求 bundle/manifest；`result_meta` 须为非空对象（字段表在实现中定稿，可与 backup 略异）
- [x] 8.5 单测或集成测：**expire** Schedule 触发一次入队与成功路径（可 mock pgbackrest 可执行文件）

## 9. 合入门槛（每阶段可运行）

- [x] 9.1 `pytest` 相关新增/更新用例通过；`ruff`/`mypy`（若项目启用）无新增违规
- [x] 9.2 控制面 + Agent + MinIO/S3 与外部 PG 的 **最小联调步骤** 写入 `console/README.md` 或 `website/docs/engineering/postgresql-pgbackrest-physical-backup.md` 附录，保证按文档可走通 **一次 FULL** 与 **一次 expire**（或 mock）
- [x] 9.3 `openspec validate add-pgbackrest-phase1-backup --strict` 通过

## 10. 提案收尾

- [x] 10.1 实现全部完成后将本 `tasks.md` 勾选为 `[x]`，并准备 `/opsx:apply` 归档流程（按团队规范）

## 11. 演示栈：目标 PostgreSQL + 含 pgBackRest 的 Agent（新增范围）

> 本节为 **提案更新** 后增量交付；完成前 **勿** 将整份变更视为可归档闭环。

- [x] 11.1 在 `deploy/docker-compose.yml` 增加 **独立** `postgres-pgbr-demo`（名称可微调）服务：与健康检查、**仅演示** 的认证/备份角色初始化（`init` SQL 或自定义 entrypoint）；**不** 占用控制面 `postgres` 服务语义。
- [x] 11.2 **（方案 A）** 在 `deploy/Dockerfile` 中安装 **pgbackrest** CLI 及运行时依赖（`apt-get` 或等价）；**不** 新增独立 `Dockerfile.agent-pgbackrest`；与目标 PG 大版本兼容策略在 PR 描述中写明。
- [x] 11.3 `agent` / `agent2` 使用上述同一镜像；在 `deploy/docker-compose.yml` 中为二者注入 **MinIO 兼容** 的 `PGBACKREST_REPO1_S3_*`（及可选 endpoint），与 `policy.config` 中 `repo_s3_*` 字段对齐；保证容器间网络可达 `postgres-pgbr-demo` 与 `minio`。
- [x] 11.4 （可选）`deploy/scripts/bootstrap_demo_stack.py`：在环境开关为真时幂等创建演示 `postgres_pgbackrest` Policy + `bound_agent_id` + 可选一次手动触发说明；**禁止** 将 S3 密钥写入 `policies.config`。
- [x] 11.5 更新 `deploy/docker-compose.yml` 顶部注释块、`deploy/.env.stack.example`（若有）、`website/docs/engineering/postgresql-pgbackrest-physical-backup.md` 附录 A：**服务名、端口、stanza、repo prefix、Agent 环境变量** 对照表；`make demo-stack-up` 验证步骤：**一次 FULL**（及文档化的 **expire**）。
- [x] 11.6 `openspec validate add-pgbackrest-phase1-backup --strict` 在文档与 spec 更新后仍通过。
