# DeVault 开发设计文档（文件备份优先版）

> **文档角色**：指导实现与排期的工程级设计说明。  
> **与 `docs/README.md` 的关系**：`README.md` 描述产品愿景与能力全景；本文档约定**开发顺序、模块边界、接口与数据模型**，并明确**先做文件备份/恢复，再做数据库备份**。  
> **读者**：实现者本人、后续维护者、代码评审。

---

## 1. 文档信息

| 项 | 内容 |
|----|------|
| 项目名称 | DeVault |
| 交付策略 | **阶段一：文件备份与恢复** → **阶段二：数据库备份与恢复** |
| 技术栈基线 | Python 3.12+、FastAPI、SQLAlchemy 2.x、Celery、Redis、PostgreSQL（平台元数据）、对象存储（MinIO / S3 兼容） |
| 默认部署 | Docker Compose（单机 / Homelab） |

---

## 2. 背景与目标

### 2.1 为何调整顺序（文件优先）

1. **依赖更少**：文件备份不强制要求目标机安装 `pg_dump` / 客户端库即可先做通「采集 → 打包 → 上传 → 元数据 → 恢复」全链路。  
2. **通用价值高**：配置文件、证书、静态资源、小型 SQLite 文件、项目目录等均属于「文件」，可先服务真实场景。  
3. **架构可复用**：存储抽象、任务状态机、Worker、调度、校验、加密、分片上传等能力，与数据库插件**同一套流水线**，先做文件有利于把平台骨架打稳，再挂数据库插件。  
4. **风险前置**：大文件、权限、符号链接、路径安全等问题在文件域最先暴露，便于尽早设计边界与测试。

### 2.2 阶段目标定义

| 阶段 | 名称 | 成功标准（可验收） |
|------|------|-------------------|
| **S1** | 文件备份 MVP | 对指定目录/文件完成一次全量备份，产物落本地或 MinIO；可列出历史；可对**新路径**完成恢复且校验一致。 |
| **S2** | 文件备份产品化 | 定时调度、失败重试、基础指标与结构化日志、CLI + 最小 Web UI、Compose 一键部署。 |
| **S3** | 数据库备份 MVP | PostgreSQL（必选）、MySQL（必选）至少一种全量逻辑备份走通同一套任务与存储模型；恢复流程可文档化执行。 |

---

## 3. 范围与非目标

### 3.1 阶段一（文件）范围内

- 全量备份：单路径或多路径、可选 glob / 排除规则。  
- 打包：流式写入压缩包（推荐 **tar + zstd** 或 **tar.gz**；实现期二选一写死一种 v1 格式，避免兼容爆炸）。  
- 存储后端：**本地目录**、**S3 兼容**（MinIO 优先联调）。  
- 校验：**SHA-256**（分块流式计算，避免整包进内存）。  
- 可选：**对称加密**（AES-GCM，密钥来自环境变量或后续密钥文件）。  
- 任务：创建、手动触发、查询状态、列表、取消（尽力而为）、重试策略。  
- 恢复：下载 artifact → 校验 → 解压到用户指定目标目录（**禁止默认覆盖**未确认路径，见安全节）。

### 3.2 阶段一明确不做（非目标）

- 跨机远程文件系统同步（rsync 式持续同步）、双向同步。  
- 块级增量、文件级增量（可记为 **S2+  backlog**，不在 S1 必达）。  
- 多租户、权限 RBAC、计费。  
- 在 Worker 容器内直接备份**任意宿主机路径**（Docker 下需通过 **挂载卷** 显式声明，见部署节）。  
- 企业合规（WORM、Legal Hold）与磁带网关。

### 3.3 阶段二（数据库）范围内（概要）

- PostgreSQL：`pg_dump` 自定义格式或 plain SQL（实现期选定一种默认）。  
- MySQL：`mysqldump` 或 `mariadb-dump`（与镜像版本对齐）。  
- 与文件任务共用：**同一任务表、状态机、存储上传、元数据记录**；插件仅替换「采集与恢复命令」部分。

### 3.4 阶段二暂不做（可列 backlog）

- PITR、WAL/binlog 增量。  
- 无代理远程数据库「平台主动连公网 IP」的安全模型（需单独设计网络与凭证）。

---

## 4. 术语

| 术语 | 含义 |
|------|------|
| **Job** | 一次备份或恢复的业务任务实例（对应一条任务记录 + 队列消息）。 |
| **Artifact** | 一次备份产生的不可变二进制产物（压缩包或 dump 文件）+ 附属 manifest。 |
| **Manifest** | 描述 artifact 的元 JSON：版本、算法、路径列表哈希、校验和、加密参数摘要等。 |
| **Plugin** | 备份/恢复策略实现（文件、Postgres、MySQL…）。 |
| **Storage Backend** | 对象存储或本地落盘抽象。 |

---

## 5. 总体架构

与 `docs/README.md` 第五章一致，实现期保持边界清晰：

```text
                 +----------------+
                 |  Web UI (S2)   |
                 +--------+-------+
                          |
                     REST API (FastAPI)
                          |
+-------------------------+-------------------------+
|  Auth(占位) / Jobs / Artifacts / Schedules / ...   |
+-------------------------+-------------------------+
          |                           |
     PostgreSQL                    Redis
   (平台元数据)              (Broker + Cache + Lock)
          |
          v
+-------------------------+
|  Scheduler (APScheduler)|
|  Cron -> enqueue Celery |
+-------------------------+
          |
          v
+-------------------------+
|  Celery Workers         |
|  file_plugin / db_*     |
+-------------------------+
          |
          v
+-------------------------+
|  StorageBackend         |
|  Local / S3-Compatible  |
+-------------------------+
```

**原则**：API 只做编排与元数据；**重 IO 在 Worker**；Scheduler 只负责触发与幂等入队。

---

## 6. 核心领域模型

### 6.1 实体关系（逻辑）

- `BackupPolicy`（策略）：名称、类型（`file` | `postgres` | …）、配置 JSON、启用状态。  
- `Schedule`：Cron、关联 policy、并发策略。  
- `Job`：一次运行；关联 policy、触发方式（manual/scheduled）、状态机、开始结束时间、错误码、worker 信息。  
- `Artifact`：属于某次成功的 backup job；存储 key、大小、checksum、manifest_key、加密标记、保留策略到期时间。  
- `RestoreJob`（可选独立表或与 `Job` 统一用 `job_type` 区分）：关联源 artifact、目标路径、状态。

**建议**：第一版可用一张 `jobs` 表 + `job_kind`（`backup`/`restore`）+ `plugin`（`file`/`postgres`/…）减少表扩散；`artifacts` 独立表便于生命周期清理。

### 6.2 `jobs` 表字段草案

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | |
| kind | enum | `backup` / `restore` |
| plugin | enum | `file` / `postgres` / `mysql` / … |
| status | enum | 见状态机 |
| policy_id | UUID FK nullable | 手动任务可无 |
| trigger | enum | `manual` / `scheduled` |
| idempotency_key | string unique nullable | 防重复入队 |
| config_snapshot | JSONB | 任务创建时的配置快照，避免 policy 被改后历史不可复现 |
| started_at / finished_at | timestamptz | |
| error_code / error_message | text | 对用户与日志友好 |
| trace_id | string | 可观测性关联 |

### 6.3 `artifacts` 表字段草案

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | |
| job_id | UUID FK | 对应成功的 backup job |
| storage_backend | string | `local` / `s3` |
| object_key | string | 桶内唯一路径，建议含 `tenant占位/日期/job_id/` |
| size_bytes | bigint | |
| checksum_sha256 | string | |
| manifest_key | string | manifest 独立对象或同包内记录二选一 |
| compression | string | 如 `tar.zst` |
| encrypted | bool | |
| created_at | timestamptz | |
| retain_until | timestamptz nullable | 生命周期 |

### 6.4 文件插件配置 JSON Schema（v1 草案）

备份策略中 `config` 示例（存 JSONB，API 校验）：

```json
{
  "version": 1,
  "paths": ["/data/app", "/etc/nginx/nginx.conf"],
  "excludes": ["**/.git/**", "**/node_modules/**"],
  "follow_symlinks": false,
  "preserve_uid_gid": true,
  "one_filesystem": false
}
```

**校验规则**：

- `paths` 非空数组；每项为绝对路径字符串。  
- `excludes` 使用 gitignore 风格或 glob 子集（实现期必须写清支持的 pattern 语法文档）。  
- `follow_symlinks` 默认 `false` 更安全。

---

## 7. 任务状态机

与产品文档一致，**实现期不得随意增删状态**（避免 UI/监控/告警分裂）。

```text
PENDING -> RUNNING -> UPLOADING -> VERIFYING -> SUCCESS
                  \-> FAILED
                  \-> RETRYING -> ...
```

- **RUNNING**：本地打包与流式哈希计算。  
- **UPLOADING**：写入 StorageBackend。  
- **VERIFYING**：可选服务端再算哈希或仅信任 Worker 上报 + 抽样校验（实现期二选一，文档写死）。  
- **RETRYING**：由 Celery `autoretry_for` + 自定义退避或独立子状态机触发。

**幂等**：`(policy_id, scheduled_window_start)` 或 `idempotency_key`（手动）在入队前 Redis 分布式锁 + DB 唯一约束。

---

## 8. 文件备份插件设计（阶段一详设）

### 8.1 插件接口（与 README 对齐，细化签名）

```python
# 概念接口：具体模块路径实现时统一命名空间 devault.plugins.*

class BackupPlugin(Protocol):
    plugin_name: str  # "file"

    async def validate_config(self, config: dict) -> None: ...
    async def estimate_size(self, config: dict) -> int | None: ...  # 可选

    async def backup(
        self,
        *,
        job_id: str,
        config: dict,
        storage: StorageBackend,
        progress: ProgressReporter,
        cancel_token: CancellationToken,
    ) -> BackupResult: ...

    async def restore(
        self,
        *,
        job_id: str,
        artifact: ArtifactRef,
        target_config: dict,
        storage: StorageBackend,
        progress: ProgressReporter,
        cancel_token: CancellationToken,
    ) -> None: ...
```

`BackupResult` 至少包含：`artifact_ref`、`checksum_sha256`、`size_bytes`、`manifest`。

### 8.2 打包格式（v1）

**推荐默认**：`tar` 流 + `zstd` 压缩（若依赖受限可退化为 `gzip`）。  

**包内布局**：

```text
artifact.tar.zst
  ├── manifest.json          # 第一个写入或最后外挂独立文件（推荐外挂 manifest 小文件便于 HEAD）
  └── payload/               # 或直接 tar 根目录为备份树
```

`manifest.json` 字段建议：

| 字段 | 说明 |
|------|------|
| schema_version | 固定 `1` |
| created_at | ISO8601 |
| plugin | `file` |
| paths | 配置快照 |
| file_manifest | 每个文件的相对路径、size、mtime、mode、sha256（大目录可配置是否逐文件哈希，影响备份时长） |
| archive_format | `tar.zst` |

**v1 性能权衡**：默认仅 **整包 SHA-256** + tar 内记录 mtime/size；逐文件 sha256 作为可选开关 `deep_integrity: true`。

### 8.3 Worker 执行步骤（备份）

1. 加载 `config_snapshot`，`validate_config`。  
2. 创建临时工作目录 `work/{job_id}/`。  
3. 打开管道：`tar` 输出 → `zstd` → `hasher` → `storage.upload_stream()`。  
4. 上传并行写入 `manifest`（可先写临时文件再上传）。  
5. 完成 `VERIFYING`：对比 `Content-Length` 与流式哈希（若有服务端 ETag 规则也记录）。  
6. 写 `artifacts` 行，job `SUCCESS`。  
7. 清理临时目录；异常则 `FAILED` 并保留可配置天数的诊断日志路径（不含敏感数据）。

### 8.4 Worker 执行步骤（恢复）

1. 根据 `artifact_id` 拉取 manifest 与 artifact。  
2. 校验哈希；若加密则解密流。  
3. 目标目录 `target_path` 必须在允许列表内或为本次 API 显式传入的**绝对路径**；若目录非空 → **默认拒绝**或要求 `force_empty=false` + 用户传 `confirm_overwrite=true`（API 层实现）。  
4. 解压并恢复 mode/mtime（在容器内 uid/gid 映射可能无意义，文档说明）。  
5. 恢复 job 完成。

### 8.5 错误分类（用于 error_code）

| error_code | 场景 |
|------------|------|
| `PATH_NOT_FOUND` | 配置路径不存在 |
| `PATH_NOT_ALLOWED` | 路径未在挂载白名单内（容器部署） |
| `STORAGE_QUOTA` | 存储端空间或配额错误 |
| `UPLOAD_TIMEOUT` | 上传超时 |
| `CHECKSUM_MISMATCH` | 校验失败 |
| `CANCELLED` | 用户取消 |

---

## 9. 存储抽象层

### 9.1 接口方法

```python
class StorageBackend(Protocol):
    async def put_stream(self, key: str, stream: AsyncIterable[bytes], *, content_length: int | None) -> PutResult: ...
    async def get_stream(self, key: str) -> AsyncIterable[bytes]: ...
    async def delete(self, key: str) -> None: ...
    async def head(self, key: str) -> ObjectMeta: ...
```

### 9.2 对象 Key 规范

`devault/{env}/artifacts/{yyyy}/{mm}/{dd}/{job_id}/bundle.tar.zst`  
`devault/{env}/artifacts/.../manifest.json`

**env**：`dev` / `prod` 来自配置，避免桶共用冲键。

---

## 10. API 设计（REST 草案）

版本前缀：`/api/v1`。

### 10.1 Policies

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/policies` | 创建策略（file / 日后 db） |
| GET | `/policies` | 列表 |
| GET | `/policies/{id}` | 详情 |
| PATCH | `/policies/{id}` | 更新 |
| DELETE | `/policies/{id}` | 软删或禁用 |

### 10.2 Jobs

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/jobs/backup` | body: `policy_id` 或内联 `plugin+config` |
| POST | `/jobs/restore` | body: `artifact_id`, `target` |
| GET | `/jobs/{id}` | 状态 |
| GET | `/jobs` | 分页筛选 |
| POST | `/jobs/{id}/cancel` | 尽力取消 |

### 10.3 Artifacts

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/artifacts` | 列表 |
| GET | `/artifacts/{id}` | 元数据 |
| GET | `/artifacts/{id}/download` | 可选预签名 URL 或仅内部（默认不暴露公网） |

### 10.4 Schedules

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/schedules` | Cron + policy_id |
| GET/PATCH/DELETE | `/schedules/...` | 标准 CRUD |

**OpenAPI**：由 FastAPI 自动生成；集成测试可对关键路径做契约测试。

---

## 11. CLI 设计（与文件优先一致）

```bash
devault file backup --policy <id>
devault file backup --paths /data --exclude '**/.git/**' --storage local --dest /backups
devault file restore --artifact <id> --to /restore-here
devault job status <job_id>
devault artifact list
```

CLI 与 API 共用同一套 client SDK（内部 Python 包）以避免重复逻辑。

---

## 12. Web UI（S2）

最低限度页面：

1. **Policies**：列表 + 创建文件策略表单。  
2. **Jobs**：列表、状态、错误信息、跳转日志。  
3. **Artifacts**：列表、恢复入口（弹窗确认路径）。  
4. **Schedules**：Cron 编辑器 + 下次运行时间预览（可用库）。

技术选型若与 README 不一致需在实现前修正本文档（例如 React + Vite 或全栈模板）。

---

## 13. 调度与队列

- **APScheduler** 扫描 `schedules` 表，到期发送 Celery task `execute_policy(policy_id, window_start)`。  
- Celery 队列建议拆分：`file_backup`、`file_restore`、`db_backup`（后期）避免大文件阻塞小任务。  
- **并发**：同一 `policy_id` 默认互斥（分布式锁），避免重叠备份。

---

## 14. 安全设计

### 14.1 路径与命令注入

- 所有路径必须经过 `pathlib` 解析与 **根边界检查**；禁止 `..` 逃逸。  
- 禁止 `shell=True`；外部进程仅允许固定 argv（`tar`、`zstd`、`pg_dump` 等）。  
- 容器部署：**仅允许备份挂载进容器的路径**（例如只读挂载 `/host_data:/data:ro`），配置里只能写 `/data/...`。

### 14.2 密钥与加密

- 对象存储密钥来自环境变量；不进库。  
- 可选 `DEVAULT_FILE_ENCRYPTION_KEY`（32 byte base64）；密钥轮换策略 backlog。

### 14.3 API 认证

- MVP 可用 **单用户 API Token**（`Authorization: Bearer`）；多用户后续迭代。

---

## 15. 可观测性

| 类型 | 内容 |
|------|------|
| 日志 | JSON 行日志；字段 `trace_id`、`job_id`、`plugin` |
| Metrics（S2） | `backup_duration_seconds`、`backup_bytes_total`、`backup_failures_total`（label: plugin, error_code） |
| Tracing（S3+） | OpenTelemetry，跨 API → Worker |

---

## 16. 配置与环境变量

| 变量 | 说明 |
|------|------|
| `DEVAULT_DATABASE_URL` | 平台 PG |
| `DEVAULT_REDIS_URL` | Celery + 锁 |
| `DEVAULT_S3_ENDPOINT` / `KEY` / `SECRET` / `BUCKET` | MinIO 或 S3 |
| `DEVAULT_LOCAL_STORAGE_ROOT` | 本地存储根 |
| `DEVAULT_API_TOKEN` | 单用户 token |
| `DEVAULT_ENCRYPTION_KEY` | 可选 |

---

## 17. 测试策略

| 层级 | 覆盖 |
|------|------|
| 单元 | glob/exclude、路径校验、manifest 序列化、checksum 流 |
| 集成 | 本地 MinIO（testcontainers）、完整 backup→restore 循环、失败注入（网络断、磁盘满模拟） |
| 契约 | OpenAPI 快照或 schemathesis（可选） |

**黄金样例**：仓库内固定小目录 `tests/fixtures/tree_a`，每次 CI 跑通备份与恢复后逐文件 `diff -r`。

---

## 18. 数据库插件（阶段二）设计要点

在文件阶段流水线稳定后接入：

### 18.1 PostgreSQL

- Worker 镜像需包含 `pg_dump` / `pg_restore` 版本 ≥ 目标服务器兼容策略（文档说明大版本约束）。  
- 配置：`host`、`port`、`user`、`password`（来自 env 或 K8s secret 挂载）、`database`。  
- 默认：`pg_dump -Fc` 自定义格式单文件 artifact。  
- 恢复：`pg_restore` 到指定库（要求用户确认 destructive 操作）。

### 18.2 MySQL

- `mysqldump` 参数标准化：`--single-transaction`（InnoDB）、`--routines` 等按需求开关。  
- 恢复：`mysql` 客户端流式导入。

### 18.3 与文件插件差异

- 数据库任务 **artifact 即 dump 文件**，manifest 记录引擎版本、工具版本。  
- 可能需要 **侧车网络**：Worker 与 DB 在同一 compose network。

---

## 19. 目录与代码组织（Monorepo）

```text
devault/
├── packages/
│   ├── api/                 # FastAPI 应用
│   ├── worker/              # Celery app + tasks
│   ├── scheduler/           # APScheduler 进程（可与 worker 合并 v1，文档注明）
│   ├── plugins/
│   │   ├── file/
│   │   ├── postgres/        # 阶段二
│   │   └── mysql/
│   ├── storage/
│   ├── sdk/                 # CLI 与内部共用 client
│   └── core/                # domain models, state machine
├── cli/
├── web/
├── deploy/
│   └── docker-compose.yml
├── helm/                    # 后期
└── docs/
```

实现期允许 `scheduler` 与 `worker` 同进程以减少运维复杂度，**但**必须在 README 注明拆分路径。

---

## 20. 开发阶段与里程碑

> **实现状态（代码库）**：S1 与 S2 主线条已在仓库落地；S3 数据库插件仍为规划。以 `README.md` 与 API `/docs` 为准做验收。

### 20.1 S1 — 文件备份 MVP（建议 2～3 周）

- [x] Monorepo 骨架、配置加载、日志  
- [x] PG 元数据库与 Alembic 迁移  
- [x] `StorageBackend`：local + MinIO  
- [x] `file` 插件：tar.gz、sha256、manifest、上传  
- [x] Celery task：`run_backup_job` / `run_restore_job`  
- [x] FastAPI：`POST /jobs/backup`、`GET /jobs`、`GET /artifacts` 等  
- [x] 恢复：`POST /jobs/restore` + worker 解压  
- [x] 单元测试（存储 + 文件插件）  

### 20.2 S2 — 文件产品化（建议 2 周）

- [x] APScheduler 独立进程（`devault-scheduler`）+ `schedules` CRUD + `policies` CRUD  
- [x] 任务取消 / 失败重试、`celery_task_id` 记录、同 `policy_id` 备份 Redis 互斥锁  
- [x] Prometheus：`/metrics`（`devault_jobs_total`、`devault_job_duration_seconds` 等）  
- [x] CLI：`devault file|job|artifact|policy|schedule`  
- [x] Web UI（Jinja2）：`/ui/jobs|artifacts|policies|schedules`（HTTP Basic，密码为 `DEVAULT_API_TOKEN`）  
- [x] Compose 含 `scheduler` 服务 + 文档  

### 20.3 S3 — 数据库 MVP（建议 3～4 周）

- [ ] `postgres` 插件 + 镜像依赖  
- [ ] `mysql` 插件  
- [ ] API policy `type` 扩展与校验  
- [ ] 恢复流程与危险操作确认  
- [ ] 扩展集成测试矩阵（版本组合选最小）  

---

## 21. 风险与对策

| 风险 | 对策 |
|------|------|
| 大文件内存暴涨 | 全链路流式；禁止一次性读入 artifact |
| tar 稀疏文件 / 特殊文件 | 文档声明不支持类型；备份前扫描告警 |
| 时区与夏令时 | 全用 UTC 存库；展示 localized |
| MinIO 与 AWS S3 行为差异 | 存储抽象集成测试双跑（可选） |
| 数据库版本不兼容 | 镜像标注支持矩阵；任务前 `pg_dump --version` 预检 |

---

## 22. 验收清单（发布前自检）

- [ ] 新用户按 `deploy/docker-compose.yml` 可在 15 分钟内完成首次文件备份。  
- [ ] 恢复目录可在 UI 或 CLI 指定，默认不静默覆盖非空目录。  
- [ ] 任务失败时用户可看到 `error_code` + 简要说明 + 日志关联 `job_id`。  
- [ ] 文档列出：支持的路径语法、限制、与数据库阶段的 roadmap 链接。

---

## 23. 修订记录

| 版本 | 日期 | 说明 |
|------|------|------|
| 0.1 | 2026-05-07 | 初版：文件优先、数据库次之完整开发设计 |
| 0.2 | 2026-05-08 | 对齐实现：S2（策略/定时/取消重试/锁/指标/简易 UI/scheduler 进程） |

---

**说明**：若后续实现与本文档冲突，应**先改文档再改代码**或在同 PR 中同步修订，避免个人项目长期「文档与行为两张皮」。
