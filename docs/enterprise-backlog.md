# DeVault 企业级落地待办清单

> **文档目的**：在 [`development-design.md`](./development-design.md) 与 [`target-architecture.md`](./target-architecture.md) 之上，结合当前代码实现，列出使项目**可长期作为企业级备份方案**交付所需的完整待办项，便于排期、分工与验收。  
> **基线说明（截至文档编写时的实现）**：S1/S2 文件备份主路径已落地；执行单元为**边缘 Agent（Pull + gRPC 租约）**，Celery Worker 已移除；控制面为 FastAPI + 内嵌 gRPC + APScheduler + PostgreSQL + Redis；对象存储以 **S3 兼容 + 预签名 URL** 为主路径；`development-design.md` 第 20 节中 **S3 数据库 MVP 仍为未完成**。

---

## 如何使用本文档

| 列 | 含义 |
|----|------|
| **阶段** | 建议实施顺序；同阶段内可按业务优先级调整。 |
| **优先级** | P0：安全与架构底线；P1：可靠性/规模；P2：功能扩展；P3：合规与运营增强。 |
| **依赖** | 实施前建议满足的前置项。 |

完成某项后，可将 `[ ]` 改为 `[x]`，并在 PR 或修订记录中注明。

---

## 零、已达成基线（供对照，非待办）

以下能力已在仓库中具备，企业化演进应**保持兼容**而非推倒重来。

- [x] 文件全量备份/恢复：`tar.gz`、流式 SHA-256、manifest、路径前缀校验（`allowed_path_prefixes`）
- [x] 元数据：PostgreSQL + Alembic；Job / Artifact / Policy / Schedule 模型
- [x] 调度：`devault-scheduler`（APScheduler）+ Cron；策略与定时任务 CRUD
- [x] 任务：取消、失败重试、同 `policy_id` 备份 Redis 互斥锁、租约与过期回收
- [x] 边缘执行：Agent `LeaseJobs` → `RequestStorageGrant` → 直传对象存储 → `CompleteJob`
- [x] 观测：Prometheus 指标、`/metrics`
- [x] 人机入口：HTTP API、CLI、简易 Web UI（HTTP Basic + `DEVAULT_API_TOKEN`）
- [x] Compose 一键演示部署（含 MinIO、Agent 挂载示例数据）
- [x] **应用版本号（单仓单版本）**：`pyproject.toml` 与 `devault.__version__` 均为 `0.1.0`；Agent 启动日志会打印该版本；**尚无**控制面与 Agent 之间的协议级版本交换与兼容性校验。

---

## 一、阶段 A：与《目标架构》对齐的硬性缺口（网络、身份、入口）

**目标**：满足「出站 HTTPS」「经网关」「生产可审计」的最低企业部署形态。

| 状态 | 优先级 | 待办项 | 说明与验收要点 |
|------|--------|--------|----------------|
| [x] | P0 | **gRPC 传输加密** | Agent `grpc.secure_channel` + CA/可选客户端证书；控制面 `grpc.ssl_server_credentials`（`DEVAULT_GRPC_SERVER_TLS_*`）。见 [`docs/grpc-tls.md`](./grpc-tls.md)。 |
| [x] | P0 | **独立 gRPC 网关或等价物** | **Envoy** 可复现示例：`deploy/envoy/envoy-grpc-tls.yaml`、`deploy/docker-compose.grpc-tls.yml`；文档区分内网明文与对外 TLS。 |
| [x] | P0 | **网关层限流与连接治理** | 控制面 **每 peer 令牌桶**（`DEVAULT_GRPC_RPS_PER_PEER` / `DEVAULT_GRPC_RPS_BURST_PER_PEER`）；网关侧 Envoy 限流可在后续加 `local_rate_limit` filter。 |
| [x] | P1 | **网关与审计日志** | 每 RPC 一行 JSON → logger **`devault.grpc.audit`**（`rpc`、`peer`、`grpc_code`、`elapsed_ms`、`extra`）；不含密钥。 |
| [x] | P1 | **Register / 令牌模型（相对共享 API Token）** | **`Register` RPC**：`DEVAULT_GRPC_REGISTRATION_SECRET` 换取当前 `DEVAULT_API_TOKEN`（引导式）；**每 Agent 短期令牌 / 吊销列表 / Redis 会话**仍为后续增强。 |
| [x] | P1 | **mTLS（可选但建议产品化）** | 控制面 **`DEVAULT_GRPC_SERVER_TLS_CLIENT_CA_PATH`** 要求客户端证书；Agent **`DEVAULT_GRPC_TLS_CLIENT_*`**；Envoy 侧校验见 `docs/grpc-tls.md` 演进说明。 |
| [x] | P2 | **gRPC 健康检查与就绪探针** | 注册 **`grpc.health.v1.Health`**（`""` 与 `devault.agent.v1.AgentControl` 均为 SERVING）；文档给出 `grpc_health_probe` 示例。 |

**依赖**：无（可与阶段 B 并行设计 `.proto` 扩展以承载 Register 响应字段）。

---

## 二、阶段 B：数据面可靠性（大对象、弱网、与目标文档一致）

**目标**：与 `target-architecture.md` 中「分块上传、断点续传、校验」及序列图中的 `CompleteMultipart` 对齐。

| 状态 | 优先级 | 待办项 | 说明与验收要点 |
|------|--------|--------|----------------|
| [ ] | P0 | **S3 分块上传（Multipart）** | 大 artifact 走 `CreateMultipartUpload` / `UploadPart` / `CompleteMultipart`；预签名策略扩展（多 URL 或会话式凭证）。 |
| [ ] | P0 | **断点续传与重试策略** | Agent 侧记录已上传 Part ETag；失败后可续传；与控制面 `CompleteJob` 校验对象存在性逻辑一致。 |
| [ ] | P1 | **恢复侧大文件流式下载** | 当前预签名恢复路径若存在整包进内存风险，改为流式写入磁盘并边下边校验（与 `development-design.md` 风险表「禁止一次性读入 artifact」一致）。 |
| [ ] | P1 | **预签名权限最小化** | 按 job、按 key 前缀限制；WRITE 与 READ 分离；过期时间与作业 SLA 对齐；文档化各云厂商差异（MinIO vs AWS）。 |
| [ ] | P2 | **可选 STS / 临时 IAM 角色** | 在云托管部署中，控制面用 IAM 角色代发临时凭证，替代长寿命控制面 AK/SK（与目标文档「IAM 临时凭证视部署而定」一致）。 |

**依赖**：阶段 A 中存储授权接口需能承载「多 part」或「会话 token」语义。

---

## 三、阶段 C：`development-design.md` S3 与产品能力补全

**目标**：完成已承诺的**数据库备份 MVP**，并关闭设计文档与实现之间的已知差距。

| 状态 | 优先级 | 待办项 | 说明与验收要点 |
|------|--------|--------|----------------|
| [ ] | P0 | **`postgres` 插件（Agent 可执行）** | `pg_dump`（或选定默认格式）；manifest 含引擎版本与工具版本；与现有 Job/Artifact/租约模型一致。 |
| [ ] | P0 | **`mysql` 插件（Agent 可执行）** | `mysqldump` / `mariadb-dump` 与镜像版本矩阵；参数标准化（如 `--single-transaction` 等可配置）。 |
| [ ] | P0 | **Policy `type` / 配置校验扩展** | API 与 DB 层对数据库类 policy 的校验、敏感字段不落日志。 |
| [ ] | P0 | **数据库恢复流程与危险操作确认** | UI/CLI/API 双重确认、文档化步骤；与文件恢复类似的「非空目录确认」策略。 |
| [ ] | P1 | **集成测试矩阵（最小版本组合）** | 文档 20.3 与 21 节：选 1～2 组 PG/MySQL 版本在 CI 或夜间流水线跑通。 |
| [ ] | P1 | **更新 `development-design.md` 目录结构描述** | 文档仍写 `Celery worker` 包路径；需与当前「Agent + 无 Celery」结构对齐，避免新成员误读。 |
| [ ] | P2 | **验收清单 22 节全部勾选** | 15 分钟首次备份、错误可见性、限制与 roadmap 链接等（见设计文档 §22）。 |

**依赖**：阶段 B 对大 dump 文件的分块上传应优先于或并行于本阶段，否则企业库备份易失败。

---

## 四、阶段 D：租户、隔离与访问控制（企业多团队/SaaS）

**目标**：`target-architecture.md` 中的 **`env/tenant/job_id` 前缀** 与多客户运营；`development-design.md` 曾列为阶段一非目标，企业化需单独立项。

| 状态 | 优先级 | 待办项 | 说明与验收要点 |
|------|--------|--------|----------------|
| [ ] | P0 | **租户模型** | `Tenant`（或 Organization）实体；Job、Policy、Schedule、Artifact 外键关联；对象存储 key 含 `tenant_id` 段。 |
| [ ] | P0 | **API 与 UI 作用域** | 所有读写按租户过滤；禁止跨租户 ID 枚举。 |
| [ ] | P1 | **RBAC** | 角色：如 Admin、Operator、Auditor；权限矩阵（创建策略、触发备份、恢复、只读审计）。 |
| [ ] | P1 | **SSO / OIDC（可选）** | 替代或并存于 HTTP Basic；与企业 IdP 集成。 |
| [ ] | P2 | **计费与用量埋点** | 存储字节、API 调用、作业次数（若 SaaS 化）。 |

**依赖**：阶段 A 的身份模型应预留 `tenant_id` 与主体绑定。

---

## 五、阶段 E：数据治理、加密与合规

**目标**：满足常见企业安全问卷；对齐 `target-architecture.md` 统一存储侧的「生命周期与合规扫描」叙述。

| 状态 | 优先级 | 待办项 | 说明与验收要点 |
|------|--------|--------|----------------|
| [ ] | P1 | **Artifact 加密（可选到默认）** | 设计文档 §3.1 中的对称加密（如 AES-GCM）；密钥来源：KMS、信封加密或客户托管密钥（CMK）方案选型文档。 |
| [ ] | P1 | **静态加密与 `encrypted` 字段真实性** | 当前完成路径写死 `encrypted=False`；与 manifest、DB 字段一致。 |
| [ ] | P1 | **保留策略与生命周期** | 按策略自动标记删除/过渡存储类；控制面任务或异步作业清理过期 artifact 元数据与对象；与 README 中「生命周期管理」承诺对齐。 |
| [ ] | P2 | **WORM / 对象锁定（Object Lock）** | 法规保留期；需存储层与策略引擎联合设计（`development-design.md` 曾列为非目标，企业版 backlog）。 |
| [ ] | P2 | **Legal Hold** | 暂停保留期删除；审计记录。 |
| [ ] | P2 | **BYOB（客户自带 Bucket）** | `target-architecture.md` §8 后续扩展；跨账号角色与凭证签发仍保持数据面不经 gRPC 传文件。 |

---

## 六、阶段 F：控制面高可用、灾备与可运维性

| 状态 | 优先级 | 待办项 | 说明与验收要点 |
|------|--------|--------|----------------|
| [ ] | P1 | **元数据库备份与恢复 Runbook** | PG 逻辑备份、PITR（控制面自身）；RTO/RPO 目标文档化。 |
| [ ] | P1 | **gRPC 服务多实例部署指南** | 无状态租约 + Redis 锁已部分具备；补充会话亲和性说明、水平扩缩步骤。 |
| [ ] | P1 | **Agent 批量管理** | 版本查询、强制升级策略、与控制面协议版本协商（`.proto` 版本号）。 |
| [ ] | P2 | **Helm Chart / K8s 清单** | `development-design.md` §19 已列 `helm/` 为后期；Operator 可作为更后阶段。 |
| [ ] | P2 | **告警路由** | Prometheus 规则 + Alertmanager 或云监控；关键失败率、租约失败、存储配额。 |

---

## 七、阶段 G：备份验证与持续信任

| 状态 | 优先级 | 待办项 | 说明与验收要点 |
|------|--------|--------|----------------|
| [ ] | P1 | **自动恢复演练 Job** | 周期性从 artifact 恢复到隔离目录、校验 checksum、写报告（README 中「临时恢复演练」产品化）。 |
| [ ] | P1 | **备份完整性告警** | 连续失败、校验失败、超窗未完成。 |
| [ ] | P2 | **增量与时间线（长期）** | WAL/binlog、PITR（`development-design.md` §3.4 非目标）；单独 Epic，依赖数据库插件成熟。 |

---

## 八、阶段 H：文档与对外形态

| 状态 | 优先级 | 待办项 | 说明与验收要点 |
|------|--------|--------|----------------|
| [ ] | P1 | **企业部署参考架构** | 单页图：DMZ、网关、控制面 VPC、对象存储、出站策略；与 `target-architecture.md` 互链。 |
| [ ] | P1 | **安全白皮书摘要** | 信任边界、密钥流、审计面、合规路线图（含明确不支持的项）。 |
| [ ] | P2 | **`docs/README.md` 与实现差距表** | 愿景章节中尚未实现的条目（Docker 自动发现、Volume 快照等）标注「规划中 / 未实现」，避免销售与交付预期错位。 |

---

## 九、阶段 I：版本管理、双端兼容与变更记录

**目标**：可重复发布、可审计升级；**控制面**与 **Agent** 版本可观测、可协商；升级后能在连接/租约阶段发现**不兼容组合**，避免静默行为错误或数据损坏。与 `proto/agent.proto` 中 `package devault.agent.v1` 的 **API 版本**区分：`v1` 为 protobuf 语义版本；**应用发行版**（如 `1.4.2`）建议独立跟踪。

### 9.1 建议维护的版本维度

| 维度 | 说明 | 典型载体 |
|------|------|-----------|
| **发行版（Release）** | 面向运维/客户的 SemVer（`MAJOR.MINOR.PATCH`）；控制面镜像与 Agent 二进制/OCI 共用一个版本号或「同次 tag 双制品」。 | Git tag、`pyproject.toml` / `devault.__version__`、容器 labels |
| **控制面构建信息** | 可选：`git sha`、构建时间；便于排障与合规溯源。 | HTTP `GET /version` 或 gRPC 自定义 metadata / 专用 RPC |
| **Agent 构建信息** | 与控制面对称；Heartbeat 或 Register 中上报。 | 环境变量注入 CI、`devault-agent --version` |
| **gRPC / Protobuf API 版本** | 破坏性 RPC 字段变更时递增（如 `devault.agent.v2`）；与发行版解耦。 | `proto/`、`scripts/gen_proto.sh` |
| **策略与插件配置 schema** | 已存在 `config.version`（如文件插件 `1`）；数据库插件需延续同一模式。 | `FileBackupConfigV1`、manifest `schema_version` |

### 9.2 待办项

| 状态 | 优先级 | 待办项 | 说明与验收要点 |
|------|--------|--------|----------------|
| [x] | P0 | **仓库根 `CHANGELOG.md`** | 采用 [Keep a Changelog](https://keepachangelog.com/) 结构（`[Unreleased]` + 按版本）；与 SemVer 发布节奏绑定；**禁止**仅依赖 Git log 作为对外变更说明。 |
| [ ] | P0 | **单一事实来源（SSOT）与发布脚本** | 版本号只在一处定义（推荐 `pyproject.toml`，`devault/__init__.py` 从 metadata 读取或构建时生成）；`scripts/` 或 `hatch`/`tbump` 等一键 bump + 校验 `CHANGELOG` 已更新。 |
| [ ] | P0 | **双端版本在协议中可见** | 扩展 `HeartbeatRequest` / `HeartbeatReply`（或独立 `Handshake`/`Register` RPC）：Agent 上报 `agent_release`（SemVer）、`proto_package`（如 `devault.agent.v1`）、可选 `git_commit`；控制面返回 `server_release`、`min_supported_agent_version`、`max_tested_agent_version`、可选 `upgrade_url` / `deprecation_message`。不兼容时返回明确 gRPC 状态与可机读 `reason_code`。 |
| [ ] | P0 | **兼容性矩阵与策略文档** | `docs/` 内固定表格或机器可读 `compatibility.json`：控制面 `X.Y` 支持的 Agent 范围、protobuf 包版本；** MINOR**：向后兼容；**MAJOR**：允许破坏性变更并文档化迁移路径。 |
| [ ] | P1 | **控制面 HTTP 版本端点** | `GET /version` 返回 JSON：`version`、`git_sha`（可选）、`api`（OpenAPI 版本若有）；供负载均衡健康检查外的发布验证。 |
| [ ] | P1 | **CLI / Agent `--version`** | 与 `__version__` 一致；便于工单与自动化采集。 |
| [ ] | P1 | **CI 兼容性门禁** | 集成测试矩阵：「最新控制面 + 上一 MINOR Agent」与「上一 MINOR 控制面 + 最新 Agent」（按矩阵裁剪）；或契约测试仅针对 gRPC 消息。 |
| [ ] | P1 | **发布说明模板** | `docs/` 或 `.github`：`RELEASE.md` 模板，含：升级顺序（先控制面后 Agent 或反之）、已知不兼容、数据库迁移（Alembic）、回滚步骤。 |
| [ ] | P2 | **运行时特性协商（可选）** | Heartbeat 或 Lease 响应中带 `server_capabilities` bitset / 重复字段，避免 Agent 盲调尚未实现的 RPC（如 Multipart 未上线时优雅降级）。 |
| [ ] | P2 | **Artifact / manifest 中的 producer 版本** | manifest 记录 `devault_release` 与 `proto_package`，便于旧 artifact 被新 Agent 恢复时的行为说明。 |

**依赖**：扩展 `.proto` 后执行 `scripts/gen_proto.sh` 并全量回归；与阶段 A 的 TLS/网关文档一并说明「版本端点是否经网关暴露」。

### 9.3 CHANGELOG 编写约定（与待办 [x] 文件配套执行）

- **分类**：`Added` / `Changed` / `Deprecated` / `Removed` / `Fixed` / `Security`。
- **受众**：运维与集成方优先；破坏性变更必须高亮并指向迁移小节。
- **与 PR 关系**：合并到主分支的 user-facing 变更应在同一发布周期记入 `[Unreleased]`，发版时折叠到版本号下。

---

## 十、建议的 Epic 映射（便于项目管理）

| Epic ID | 名称 | 主要覆盖阶段 |
|---------|------|----------------|
| E-ARCH-001 | 传输安全与网关 | A |
| E-DATA-001 | 大对象与续传 | B |
| E-DB-001 | 数据库备份 MVP | C |
| E-MT-001 | 租户与 RBAC | D |
| E-GOV-001 | 加密、保留、合规 | E |
| E-OPS-001 | HA、DR、K8s、告警 | F |
| E-TRUST-001 | 验证与演练 | G |
| E-DOC-001 | 企业文档 | H |
| E-VER-001 | 版本、双端兼容与 CHANGELOG | I |

---

## 十一、修订记录

| 日期 | 变更 |
|------|------|
| 2026-05-08 | 初稿：基于 `development-design.md`、`target-architecture.md` 与当前代码实现整理企业级待办清单。 |
| 2026-05-08 | 新增阶段 I：版本管理、控制面/Agent 双端校验、CHANGELOG 约定；Epic `E-VER-001`；基线补充版本号现状。 |
| 2026-05-08 | **阶段 A 落地**：TLS/mTLS、Envoy 示例、限流与审计、`Register`、Health、`GET /version`、[`grpc-tls.md`](./grpc-tls.md)；发布 **0.2.0**。 |
