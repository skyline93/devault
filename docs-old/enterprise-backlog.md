# DeVault 企业级落地待办清单

> **文档目的**：在 [`development-design.md`](./development-design.md) 与 [**目标架构（文档站）**](../website/docs/intro/target-architecture.md) 之上，结合当前代码实现，列出使项目**可长期作为企业级备份方案**交付所需的完整待办项，便于排期、分工与验收。  
> **基线说明（截至文档编写时的实现）**：S1/S2 文件备份主路径已落地；执行单元为**边缘 Agent（Pull + gRPC 租约）**，Celery Worker 已移除；控制面为 FastAPI + 内嵌 gRPC + APScheduler + PostgreSQL + Redis；对象存储以 **S3 兼容 + 预签名 URL** 为主路径；`development-design.md` 第 20 节中 **S3 数据库 MVP 仍为未完成**。  
> **索引**：**§零～§九** 及 **§十四**（追加）每一条（含已完成）的**不删减**汇总见 **[排期波次与全量待办索引](#排期波次与全量待办索引)**（位于 **§零** 之后）；维护时请与分节表同步勾选。

---

## 如何使用本文档

| 列 | 含义 |
|----|------|
| **里程碑** | **M1** = 平台与企业级能力（建议优先）；**M2** = 在 M1 达标后接入的**新备份类型**（数据库 MVP 等）。 |
| **优先级** | P0：安全与架构底线；P1：可靠性/规模；P2：功能扩展；P3：合规与运营增强。 |
| **依赖** | 实施前建议满足的前置项（见各节末）。 |
| **原阶段字母** | 历史编号（A～I），见文末「重组对照表」，便于与旧讨论、Epic 对齐。 |
| **可增强** | 已交付主线之上的**后续增强**；表中 **`（可增强）`** 或文末 **[十三、可增强项汇总](#十三可增强项汇总)** 所列条目**不阻塞**当前里程碑，可单独排期。 |
| **排期波次** | 跨章节的建议实施顺序（**1**～**7**），与 **P0～P3** 独立；定义见 **[排期波次与全量待办索引](#排期波次与全量待办索引)**。 |
| **Web UI 同步** | **§十四 · 十四-16～十四-18**：后端迭代须与 **`/ui/*`** 同期或登记豁免；详见上文 **「整体实施路线」** 与 **§十四 · 14.3**。 |

完成某项后，可将 `[ ]` 改为 `[x]`，并在 **归属分节表**（含 **§十四**）、**全量待办索引** 与 PR / 修订记录中注明。

---

## 整体实施路线（先平台、后数据库）

**策略**：优先完成 **M1 企业级平台能力**（传输与身份、数据面可靠性、版本与兼容、租户与治理、运维与信任、对外文档），再在稳定平台上接入 **M2 数据库备份** 等新产品能力。  
**原因简述**：数据库 dump 体积大、耗时长，会放大弱网、断点续传、租约与升级兼容等问题；平台能力与其正交，先夯实可减少返工。  
**不删减原则**：下文各表合起来即为**完整**待办集合；仅调整阅读顺序与里程碑归属，**不删除**重组前已计划的条目。  
**排期原则（2026-05-09 起）**：在 **M1 波次 1～2**（基础设施闭环 + 发布/数据面韧性）未收敛前，**默认不启动 M2（§九）**；§七「增量与时间线」绑定 M2，随 **波次 6** 处理。  
**Web UI 同步原则（2026-05-10 起）**：控制面 **REST/OpenAPI** 与 **Web UI（`E-UX-001`）** 按 **竖切同期验收**——**§十四** 每条后端能力默认 **同一发布周期** 交付 **`/ui/*` 最小可用面**（列表 / 表单 / 详情至少其一）；若仅 API 先合并，须在 PR 或 **`website/docs/guides/web-console.md`** 登记 **豁免与回填截止**，并由 **十四-16** 作为流程待办持续监督直至闭合。**M2（§九）** 数据库能力须执行 **十四-18**（**波次 5**），避免「仅 curl 可用却宣称 GA」。**十四-17** 为字段一致性与 RBAC 闸门（可与 CI/PR 模板挂钩）。

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
- [x] **应用版本号（单仓单版本）**：以 `pyproject.toml` / `devault.__version__` 为准；Agent 启动日志会打印版本。
- [x] **数据面（Multipart 主线）**：S3 Multipart 大 bundle、分片上传重试、预签名恢复 **流式下载 + 分块校验**；单对象 PUT 从磁盘流式上传（见 [`s3-data-plane.md`](./s3-data-plane.md)）。
- [x] **协议级版本协商**：Heartbeat / Register 已扩展 `agent_release` / `proto_package` / 控制面 `min_supported_agent_version` 等（见 **M1 · 三、版本管理** 与 `website/docs/reference/grpc-services.md`）。

---

## 排期波次与全量待办索引

### 排期波次（建议实施顺序）

下列 **波次** 为结合当前代码实现后的**跨章节排期**（先收口 M1 基础设施与可运维性，再强化发布/数据面韧性，然后网关身份与合规扩展，最后启动 M2）。**不改变**各分节表中 **P0～P3** 的语义（安全/架构底线仍以 P0 为准）。

| 波次 | 名称 | 未完成条目（§ 指向） |
|------|------|------------------------|
| **1** | M1 基础设施与运维闭环 | **已收敛**：Helm（`deploy/helm/devault`）+ **告警路由**（`deploy/alertmanager.yml`、`deploy/docker-compose.prometheus.yml`、`monitoring.enabled`、文档 **`website/docs/install/observability.md`**） |
| **2** | 发布工程与数据面韧性 | **已收敛**：§二 Multipart×加密；§三 CI 多版本镜像 E2E；§三 **`bump_release` ↔ `compatibility.json`**；§三 Agent **`server_capabilities`** 降级 |
| **3** | 网关与身份演进 | **已收敛**：§一 Envoy **`local_rate_limit`**；§一 Register **每 Agent Redis 会话** + **`POST …/revoke-grpc-sessions`** |
| **4** | 合规与统一存储 \| **控制台与 API 对等** | **§五**：已从迁移 **`0010`** 等落地（详见 **§五**、**§十**）；**§八 Web UI**：**八-04～八-09** 已落地（`src/devault/api/routes/ui.py`、`deps.py`、`web/templates/`；与 **`website/docs/guides/web-console.md`** 同步维护）。 |
| **5** | M2 数据库备份 MVP | §九 全部未完成项 + **§十四 · 十四-18**（Web UI 与 §九 API **同期**；建议在 **波次 1～2** 收敛后再启动） |
| **6** | 长期（依赖 M2） | §七 增量与时间线 |
| **7** | M1 Agent 租户隔离与执行路由（Greenfield） | **§十四** **十四-15** 待收口（**十四-01～十四-14**、**十四-16～十七** 已收口）；与 **波次 3～4** 可部分并行；**不考虑向后兼容**，见 **§十四** 首段说明 |
| **—** | 已完成 | 全量索引中状态 `[x]` 的条目及 **§零** 基线 11 条 |

### 全量待办索引

（按章节顺序，与 **§零～§九**、**§十四** 分节表 **一一对应**；**历史条目不删减**，§十四 为 **2026-05-10** 起追加。**§十四** 正文与索引行均紧接 **§四 / 四-05** 之后、**§五 / 五-01** 之前；**十四-16～十四-18** 为 **Web UI 与 REST 同步排期** 专条。）

维护约定：**勾选状态**以 **§零～§九**、**§十四** 分节表为准；完成某项后请在本索引与归属分节表 **同步**更新 `[ ]` / `[x]`。

| 编号 | 章节 | 状态 | P | 排期 | 待办项（摘要与分节表标题一致） |
|------|------|------|---|------|------------------------------|
| 零-01 | §零 | [x] | — | — | 文件全量备份/恢复：`tar.gz`、流式 SHA-256、manifest、路径前缀校验（`allowed_path_prefixes`） |
| 零-02 | §零 | [x] | — | — | 元数据：PostgreSQL + Alembic；Job / Artifact / Policy / Schedule 模型 |
| 零-03 | §零 | [x] | — | — | 调度：`devault-scheduler`（APScheduler）+ Cron；策略与定时任务 CRUD |
| 零-04 | §零 | [x] | — | — | 任务：取消、失败重试、同 `policy_id` 备份 Redis 互斥锁、租约与过期回收 |
| 零-05 | §零 | [x] | — | — | 边缘执行：Agent `LeaseJobs` → `RequestStorageGrant` → 直传对象存储 → `CompleteJob` |
| 零-06 | §零 | [x] | — | — | 观测：Prometheus 指标、`/metrics` |
| 零-07 | §零 | [x] | — | — | 人机入口：HTTP API、CLI、简易 Web UI（HTTP Basic + `DEVAULT_API_TOKEN`） |
| 零-08 | §零 | [x] | — | — | Compose 一键演示部署（含 MinIO、Agent 挂载示例数据） |
| 零-09 | §零 | [x] | — | — | **应用版本号（单仓单版本）**：以 `pyproject.toml` / `devault.__version__` 为准；Agent 启动日志会打印版本。 |
| 零-10 | §零 | [x] | — | — | **数据面（Multipart 主线）**：S3 Multipart 大 bundle、分片上传重试、预签名恢复 **流式下载 + 分块校验**；单对象 PUT 从磁盘流式上传（见 [`s3-data-plane.md`](./s3-data-plane.md)）。 |
| 零-11 | §零 | [x] | — | — | **协议级版本协商**：Heartbeat / Register 已扩展 `agent_release` / `proto_package` / 控制面 `min_supported_agent_version` 等（见 **M1 · 三、版本管理** 与 `website/docs/reference/grpc-services.md`）。 |
| 一-01 | §一 | [x] | P0 | — | **gRPC 传输加密** |
| 一-02 | §一 | [x] | P0 | — | **独立 gRPC 网关或等价物** |
| 一-03 | §一 | [x] | P0 | — | **网关层限流与连接治理** |
| 一-04 | §一 | [x] | P1 | — | **网关与审计日志** |
| 一-05 | §一 | [x] | P1 | — | **Register / 令牌模型（相对共享 API Token）** |
| 一-06 | §一 | [x] | P1 | — | **mTLS（可选但建议产品化）** |
| 一-07 | §一 | [x] | P2 | — | **gRPC 健康检查与就绪探针** |
| 一-08 | §一 | [x] | P3 | 3 | **Envoy 网关 local_rate_limit（可增强）** |
| 一-09 | §一 | [x] | P3 | 3 | **Register 后续：每 Agent 令牌 / 吊销 / Redis 会话（可增强）** |
| 二-01 | §二 | [x] | P0 | — | **S3 分块上传（Multipart）** |
| 二-02 | §二 | [x] | P0 | — | **分片上传同进程重试** |
| 二-03 | §二 | [x] | P1 | — | **Multipart 跨重启 / 跨进程断点续传** |
| 二-04 | §二 | [x] | P1 | — | **恢复侧大文件流式下载** |
| 二-05 | §二 | [x] | P1 | — | **预签名权限最小化** |
| 二-06 | §二 | [x] | P2 | — | **STS / AssumeRole 临时凭证（控制面 → S3）** |
| 二-07 | §二 | [x] | P3 | — | **Multipart 与 Artifact 加密的联调与边界（可增强）** |
| 三-01 | §三 | [x] | P0 | — | **仓库根 `CHANGELOG.md`** |
| 三-02 | §三 | [x] | P0 | — | **单一事实来源（SSOT）与发布脚本** |
| 三-03 | §三 | [x] | P0 | — | **双端版本在协议中可见** |
| 三-04 | §三 | [x] | P0 | — | **兼容性矩阵与策略文档** |
| 三-05 | §三 | [x] | P1 | — | **控制面 HTTP 版本端点** |
| 三-06 | §三 | [x] | P1 | — | **CLI / Agent `--version`** |
| 三-07 | §三 | [x] | P1 | — | **CI 兼容性门禁** |
| 三-08 | §三 | [x] | P1 | — | **发布说明模板** |
| 三-09 | §三 | [x] | P2 | — | **运行时特性协商（可选）** |
| 三-10 | §三 | [x] | P2 | — | **Artifact / manifest 中的 producer 版本** |
| 三-11 | §三 | [x] | P2 | 2 | **CI：多版本镜像端到端矩阵（可增强）** |
| 三-12 | §三 | [x] | P3 | 2 | **发版脚本与 compatibility.json 联动（可增强）** |
| 三-13 | §三 | [x] | P3 | 2 | **Agent 基于 server_capabilities 的降级路径（可增强）** |
| 三-注 | §三.3 | — | — | — | **CHANGELOG 编写约定**（持续执行流程，非 `[ ]` 勾选项；见 **§三.3**） |
| 四-01 | §四 | [x] | P0 | — | **租户模型** |
| 四-02 | §四 | [x] | P0 | — | **API 与 UI 作用域** |
| 四-03 | §四 | [x] | P1 | — | **RBAC** |
| 四-04 | §四 | [x] | P1 | — | **SSO / OIDC（可选）** |
| 四-05 | §四 | [x] | P2 | — | **计费与用量埋点** |
| 十四-01 | §十四 | [x] | P0 | 7 | **Agent enrollment：租户绑定与注册换发凭据（Greenfield）** |
| 十四-02 | §十四 | [x] | P0 | 7 | **`LeaseJobs` 及作业全链按 `job.tenant_id` 与 Agent 授权租户硬过滤** |
| 十四-03 | §十四 | [x] | P0 | 7 | **跨租户隔离复核：artifact、预签名、S3 key、指标与审计路径** |
| 十四-04 | §十四 | [x] | P0 | 7 | **Agent 凭据吊销、轮换与 Runbook（泄露响应）** |
| 十四-05 | §十四 | [x] | P1 | 7 | **策略绑定执行目标：`agent_id` 或 `agent_pool_id`（仅绑定者可领该策略作业）** |
| 十四-06 | §十四 | [x] | P1 | 7 | **Agent 池：成员、优先级/权重、健康度与池级运维语义** |
| 十四-07 | §十四 | [x] | P1 | 7 | **调度与租约：池内 failover、同策略并发锁与失败重试是否可换实例** |
| 十四-08 | §十四 | [x] | P2 | 7 | **Heartbeat 扩展：hostname、OS、可选 region/env；允许备份路径前缀（allowlist）** |
| 十四-09 | §十四 | [x] | P2 | 7 | **持久化 Agent 快照与租户范围列表（REST/UI，替代仅全平台舰队视图）** |
| 十四-10 | §十四 | [x] | P2 | 7 | **策略创建/编辑 UX：选 Agent 或池；`paths` ⊆ allowlist 等服务端校验（租户可配置严格度）** |
| 十四-11 | §十四 | [x] | P2 | 7 | **备份路径预检 Job（一键校验存在性/可读性，结果写入任务或 `result_meta`）** |
| 十四-12 | §十四 | [x] | P2 | 7 | **作业详情：`lease_agent_id` + 领租约或完成时固化的 hostname 快照（审计对齐）** |
| 十四-13 | §十四 | [x] | P3 | 7 | **告警与 SLO：Agent 失联、策略无健康执行者、连续失败、allowlist 与策略冲突** |
| 十四-14 | §十四 | [x] | P3 | 7 | **批量注册与 IaC：API/Terraform 模板（Agent、池、策略）** |
| 十四-15 | §十四 | [ ] | P3 | 7 | **文档与 Quickstart：多租户拓扑、密钥生命周期、池 vs 单 Agent、与 NetBackup 类心智对照** |
| 十四-16 | §十四 | [x] | P1 | 7 | **交付节奏：§十四 后端与 Web UI（`E-UX-001`）竖切同期闭合或登记豁免** |
| 十四-17 | §十四 | [x] | P2 | 7 | **OpenAPI ↔ `/ui/*` 字段与 RBAC 闸门（含 auditor 只读、CHANGELOG 用户可见节）** |
| 十四-18 | §十四 | [ ] | P1 | 5 | **M2：§九 数据库 MVP 的 Web UI 与 API 同期排期（波次 5 内闭合）** |
| 五-01 | §五 | [x] | P1 | — | **Artifact 加密（可选到默认）** |
| 五-02 | §五 | [x] | P1 | — | **静态加密与 `encrypted` 字段真实性** |
| 五-03 | §五 | [x] | P2 | 4 | **KMS / 信封加密 / 按租户 CMK（可增强）** |
| 五-04 | §五 | [x] | P3 | 4 | **默认或租户级强制加密策略（可增强）** |
| 五-05 | §五 | [x] | P1 | — | **保留策略与生命周期** |
| 五-06 | §五 | [x] | P2 | 4 | **WORM / 对象锁定（Object Lock）** |
| 五-07 | §五 | [x] | P2 | 4 | **Legal Hold** |
| 五-08 | §五 | [x] | P2 | 4 | **BYOB（客户自带 Bucket）** |
| 六-01 | §六 | [x] | P1 | — | **元数据库备份与恢复 Runbook** |
| 六-02 | §六 | [x] | P1 | — | **gRPC 服务多实例部署指南** |
| 六-03 | §六 | [x] | P1 | — | **Agent 批量管理** |
| 六-04 | §六 | [x] | P2 | — | **Agent 舰队 Web UI** |
| 六-05 | §六 | [x] | P2 | — | **Helm Chart / K8s 清单** |
| 六-06 | §六 | [x] | P2 | — | **告警路由** |
| 七-01 | §七 | [x] | P1 | — | **自动恢复演练 Job** |
| 七-02 | §七 | [x] | P1 | — | **备份完整性告警** |
| 七-03 | §七 | [ ] | P2 | 6 | **增量与时间线（长期）** |
| 八-01 | §八 | [x] | P1 | — | **企业部署参考架构** |
| 八-02 | §八 | [x] | P1 | — | **安全白皮书摘要** |
| 八-03 | §八 | [x] | P2 | — | **`docs/README.md` 与实现差距表** |
| 八-04 | §八 | [x] | P1 | 4 | **Web UI：策略表单与备份配置对齐（KMS / Object Lock / 文案）** |
| 八-05 | §八 | [x] | P1 | 4 | **Web UI：租户运维（列表 / PATCH BYOB·合规字段；Admin）** |
| 八-06 | §八 | [x] | P1 | 4 | **Web UI：租户上下文与切换（多租户日常不设 curl）** |
| 八-07 | §八 | [x] | P2 | 4 | **Web UI：Artifacts 列补齐（encrypted / legal_hold）** |
| 八-08 | §八 | [x] | P2 | 4 | **Web UI：法务保留 Legal Hold（Admin 行操作 + 确认）** |
| 八-09 | §八 | [x] | P3 | 4 | **Web UI：运维快捷键（吊销 Agent gRPC 会话、密钥/CLI 文档入口）** |
| 九-01 | §九 | [ ] | P0 | 5 | **`postgres` 插件（Agent 可执行）** |
| 九-02 | §九 | [ ] | P0 | 5 | **`mysql` 插件（Agent 可执行）** |
| 九-03 | §九 | [ ] | P0 | 5 | **Policy `type` / 配置校验扩展** |
| 九-04 | §九 | [ ] | P0 | 5 | **数据库恢复流程与危险操作确认** |
| 九-05 | §九 | [ ] | P1 | 5 | **集成测试矩阵（最小版本组合）** |
| 九-06 | §九 | [ ] | P1 | 5 | **更新 `development-design.md` 目录结构描述** |
| 九-07 | §九 | [ ] | P2 | 5 | **验收清单 22 节全部勾选** |

**排期列**：`—` 表示已完成或不适用；**1～7** 为建议实施波次，含义见本节首段 **排期波次** 表。

---

# 里程碑 M1：企业级平台能力

---

## 一、传输、身份与入口（原阶段 A）

**里程碑**：M1 · **目标**：满足「出站 HTTPS」「经网关」「生产可审计」的最低企业部署形态。  
**原阶段**：A

| 状态 | 优先级 | 待办项 | 说明与验收要点 |
|------|--------|--------|----------------|
| [x] | P0 | **gRPC 传输加密** | Agent `grpc.secure_channel` + CA/可选客户端证书；控制面 `grpc.ssl_server_credentials`（`DEVAULT_GRPC_SERVER_TLS_*`）。见 [`docs/grpc-tls.md`](./grpc-tls.md)。 |
| [x] | P0 | **独立 gRPC 网关或等价物** | **Envoy** 可复现示例：`deploy/envoy/envoy-grpc-tls.yaml`、`deploy/docker-compose.grpc-tls.yml`；文档区分内网明文与对外 TLS。 |
| [x] | P0 | **网关层限流与连接治理** | 控制面 **每 peer 令牌桶**（`DEVAULT_GRPC_RPS_PER_PEER` / `DEVAULT_GRPC_RPS_BURST_PER_PEER`）；网关侧 Envoy 限流可在后续加 `local_rate_limit` filter。 |
| [x] | P1 | **网关与审计日志** | 每 RPC 一行 JSON → logger **`devault.grpc.audit`**（`rpc`、`peer`、`grpc_code`、`elapsed_ms`、`extra`）；不含密钥。 |
| [x] | P1 | **Register / 令牌模型（相对共享 API Token）** | **`Register` RPC**：引导式认证（现为 **Redis 每 Agent 会话**，见 **一-09**）；HTTP 侧仍可用 **`DEVAULT_API_TOKEN`** / API Key。 |
| [x] | P1 | **mTLS（可选但建议产品化）** | 控制面 **`DEVAULT_GRPC_SERVER_TLS_CLIENT_CA_PATH`** 要求客户端证书；Agent **`DEVAULT_GRPC_TLS_CLIENT_*`**；Envoy 侧校验见 `docs/grpc-tls.md` 演进说明。 |
| [x] | P2 | **gRPC 健康检查与就绪探针** | 注册 **`grpc.health.v1.Health`**（`""` 与 `devault.agent.v1.AgentControl` 均为 SERVING）；文档给出 `grpc_health_probe` 示例。 |
| [x] | P3 | **Envoy 网关 local_rate_limit（可增强）** | **`deploy/envoy/envoy-grpc-tls.yaml`**：`envoy.filters.http.local_ratelimit`（token_bucket **40/s** 补充、burst **80**）；与 **`DEVAULT_GRPC_RPS_PER_PEER`** 双层限流；**`website/docs/security/tls-and-gateway.md`**、**`docs-old/grpc-tls.md`** §4。 |
| [x] | P3 | **Register 后续：每 Agent 令牌 / 吊销 / Redis 会话（可增强）** | **`Register`** 经 **`mint_agent_session_token`** 签发 **Redis** 绑定 **`agent_id`** 的 Bearer（**`DEVAULT_GRPC_AGENT_SESSION_TTL_SECONDS`**）；**`_authenticate_grpc`** / **`_require_agent_bearer_matches`**；**`POST /api/v1/agents/{id}/revoke-grpc-sessions`**（admin）；仍可用 **`DEVAULT_API_TOKEN`** / API Key 作为运维令牌调 gRPC。 |

**依赖**：无（可与数据面并行设计 `.proto` 扩展以承载 Register 响应字段）。

---

## 二、数据面可靠性（原阶段 B）

**里程碑**：M1 · **目标**：与 [目标架构](../website/docs/intro/target-architecture.md) 中控制面/数据面及 Pull 序列所述「分块上传、断点续传、校验」及 `CompleteMultipart` 路径对齐。  
**原阶段**：B

| 状态 | 优先级 | 待办项 | 说明与验收要点 |
|------|--------|--------|----------------|
| [x] | P0 | **S3 分块上传（Multipart）** | 当 `bundle_content_length >= DEVAULT_S3_MULTIPART_THRESHOLD_BYTES`：`CreateMultipartUpload` + 每段 `upload_part` 预签名 + `CompleteJob` 时控制面 `complete_multipart_upload`。见 [`docs/s3-data-plane.md`](./s3-data-plane.md)。 |
| [x] | P0 | **分片上传同进程重试** | Agent 对单个分片 PUT **指数退避**重试；范围限定为 **同一进程、同一租约周期内**、当前预签名仍有效。 |
| [x] | P1 | **Multipart 跨重启 / 跨进程断点续传** | 持久化 `UploadId`、已完成 **PartNumber + ETag**（`jobs.bundle_wip_*` + Agent `~/.cache/devault-agent/multipart/<job_id>/`）；`RequestStorageGrant` 支持 **`resume_bundle_multipart_upload_id`**，控制面 **`ListParts`** 后补签缺失分片；齐片时 **`bundle_multipart_completed_parts_json`**；新 MPU / `CompleteJob` 失败时 **Abort** 孤儿上传；指标 **`devault_multipart_resume_grants_total`**。见 [`s3-data-plane.md`](./s3-data-plane.md) §3。 |
| [x] | P1 | **恢复侧大文件流式下载** | 预签名恢复改为 **httpx stream + 分块 SHA-256**，不再整包 `read_bytes()`。 |
| [x] | P1 | **预签名权限最小化** | 仍按 **job 维度** 的 object key；manifest 与 bundle 分离；TTL 与 `DEVAULT_PRESIGN_TTL_SECONDS` 对齐；云差异见 [`docs/s3-data-plane.md`](./s3-data-plane.md)。 |
| [x] | P2 | **STS / AssumeRole 临时凭证（控制面 → S3）** | 控制面通过 **STS `AssumeRole`** 获取 **短时**会话密钥，用于预签名、Multipart 控制 API 与 `head_object` 等；`DEVAULT_S3_ASSUME_ROLE_*` / `DEVAULT_S3_STS_*`；与静态 `DEVAULT_S3_ACCESS_KEY` / `SECRET` 或 boto3 **默认凭证链**（IRSA、实例配置、Vault 注入等）组合；AssumeRole 结果 **内存缓存** 至临近过期。文档：**`website/docs/storage/sts-assume-role.md`**；实现：`src/devault/storage/s3_client.py`。 |
| [x] | P3 | **Multipart 与 Artifact 加密的联调与边界（可增强）** | Agent **`validate_multipart_resume_checkpoint`**（策略 vs manifest encryption、WIP 大小）；checkpoint 增加 **`encrypt_artifacts`**；**`devault_multipart_encrypted_mpu_completes_total`**；**`docs-old/s3-data-plane.md`** §3、**`artifact-encryption.md`**、**`large-objects.md`**、**`observability.md`**；单测 **`tests/test_multipart_encrypt_checkpoint.py`**。 |

**依赖**：第一节中存储授权接口需能承载「多 part」或「会话 token」语义；**跨重启续传**依赖租约与预签名策略可扩展；**STS** 依赖云账号与信任策略落地。  
**与 M2 关系**：大 dump 强依赖 Multipart 与续传；**建议在开启数据库备份 MVP 前完成或并行关闭**「跨重启续传」主线风险。

---

## 三、版本管理、双端兼容与变更记录（原阶段 I）

**里程碑**：M1 · **目标**：可重复发布、可审计升级；**控制面**与 **Agent** 版本可观测、可协商；升级后能在连接/租约阶段发现**不兼容组合**，避免静默行为错误或数据损坏。与 `proto/agent.proto` 中 `package devault.agent.v1` 的 **API 版本**区分：`v1` 为 protobuf 语义版本；**应用发行版**（如 `1.4.2`）建议独立跟踪。  
**原阶段**：I

### 3.1 建议维护的版本维度

| 维度 | 说明 | 典型载体 |
|------|------|-----------|
| **发行版（Release）** | 面向运维/客户的 SemVer（`MAJOR.MINOR.PATCH`）；控制面镜像与 Agent 二进制/OCI 共用一个版本号或「同次 tag 双制品」。 | Git tag、`pyproject.toml` / `devault.__version__`、容器 labels |
| **控制面构建信息** | 可选：`git sha`、构建时间；便于排障与合规溯源。 | HTTP `GET /version` 或 gRPC 自定义 metadata / 专用 RPC |
| **Agent 构建信息** | 与控制面对称；Heartbeat 或 Register 中上报。 | 环境变量注入 CI、`devault-agent --version` |
| **gRPC / Protobuf API 版本** | 破坏性 RPC 字段变更时递增（如 `devault.agent.v2`）；与发行版解耦。 | `proto/`、`scripts/gen_proto.sh` |
| **策略与插件配置 schema** | 已存在 `config.version`（如文件插件 `1`）；数据库插件需延续同一模式。 | `FileBackupConfigV1`、manifest `schema_version` |

### 3.2 待办项

| 状态 | 优先级 | 待办项 | 说明与验收要点 |
|------|--------|--------|----------------|
| [x] | P0 | **仓库根 `CHANGELOG.md`** | 采用 [Keep a Changelog](https://keepachangelog.com/) 结构（`[Unreleased]` + 按版本）；与 SemVer 发布节奏绑定；**禁止**仅依赖 Git log 作为对外变更说明。 |
| [x] | P0 | **单一事实来源（SSOT）与发布脚本** | 版本号只在一处定义（**`pyproject.toml`**）；`devault.__version__` 从 **`importlib.metadata`** 读取，无安装元数据时回读仓库根 `pyproject.toml`。`scripts/bump_release.py` 折叠 `[Unreleased]` 并 bump；`scripts/verify_release_docs.py` 校验 CHANGELOG 含当前版本节；CI 见 `.github/workflows/ci.yml`。发版流程见 `website/docs/development/releasing.md`。 |
| [x] | P0 | **双端版本在协议中可见** | **`Heartbeat` / `Register`**：`agent_release`、`proto_package`、`git_commit`；回复 `server_release`、`min_supported_agent_version`、`max_tested_agent_version`、`upgrade_url`、`deprecation_message`、`reason_code`。硬失败时 **`FAILED_PRECONDITION` / `INVALID_ARGUMENT`** + trailing metadata **`devault-reason-code`**。实现见 `src/devault/grpc/agent_version.py`；文档见 `website/docs/reference/grpc-services.md`。 |
| [x] | P0 | **兼容性矩阵与策略文档** | **`docs/compatibility.json`**（矩阵、`current`、能力说明）；策略与 CI 说明见 **`website/docs/development/compatibility.md`**；**`docs/RELEASE.md`** 发版检查清单。 |
| [x] | P1 | **控制面 HTTP 版本端点** | `GET /version` 返回 `service`、`version`、`api`（`v1`）、`grpc_proto_package`、可选 **`git_sha`**（`DEVAULT_SERVER_GIT_SHA`）。 |
| [x] | P1 | **CLI / Agent `--version`** | **`devault`**、**`devault-agent`**、**`devault-scheduler`** 支持 `--version` / `-V`，与 `devault.__version__` 一致。 |
| [x] | P1 | **CI 兼容性门禁** | **`.github/workflows/ci.yml`**：`matrix.suite` 为 **`full`**（全量 pytest）与 **`compatibility`**（契约 + 版本门控切片 + **`verify_release_docs`** / **`verify_compatibility_matrix`**）。 |
| [x] | P1 | **发布说明模板** | **`docs/RELEASE.md`**：升级顺序、兼容性与 proto、不兼容与迁移、观测与密钥、回滚、发布后验证。 |
| [x] | P2 | **运行时特性协商（可选）** | **`HeartbeatReply`** / **`RegisterReply`** 增加 **`server_capabilities`**；实现见 **`devault.server_capabilities`**；与 **`docs/compatibility.json`** 对齐。 |
| [x] | P2 | **Artifact / manifest 中的 producer 版本** | 文件插件 **`manifest.json`** 增加 **`devault_release`**、**`grpc_proto_package`**（与 `release_meta` / gRPC 包一致）。 |
| [x] | P2 | **CI：多版本镜像端到端矩阵（可增强）** | **`.github/workflows/e2e-version-matrix.yml`**（**`workflow_dispatch`** + **每周一 schedule**）：Compose 使用预构建 **CP / Agent** 镜像（**`deploy/docker-compose.e2e-matrix.override.yml`**）；**`scripts/ci_e2e_matrix_plan.py`** 读 **`docs/compatibility.json`** · **`ci_e2e`**；**`scripts/e2e_grpc_register_heartbeat.py`** 在宿主机与 Agent 容器内各跑一次 **Register + Heartbeat**。**`previous_minor_git_ref`** 非空时增加「当前 SHA + 旧 ref」双向交叉行；与 **`matrices`** 的映射见 **`ci_e2e.matrix_definitions`**；文档 **`website/docs/development/compatibility.md`**。 |
| [x] | P3 | **发版脚本与 compatibility.json 联动（可增强）** | **`scripts/bump_release.py`** 在写入 **`pyproject.toml`** / **`CHANGELOG.md`** 后调用 **`sync_compatibility_current_release`**，更新 **`docs/compatibility.json`** · **`current.control_plane_release`**；**`--dry-run`** 打印将写入的版本；文档 **`website/docs/development/releasing.md`**、**`docs/RELEASE.md`**；单测 **`tests/test_bump_release_compatibility.py`**。 |
| [x] | P3 | **Agent 基于 server_capabilities 的降级路径（可增强）** | **`AgentCapabilityState`**：Register / 成功 Heartbeat 刷新 **`frozenset(server_capabilities)`**；备份路径 **`gate_multipart_resume`** / **`gate_multipart_upload`**（**`devault.agent.capabilities`**）：无 **`multipart_resume`** 则清空 checkpoint 续传；无 **`multipart_upload`** 则超过阈值仍用单对象 PUT；**`logger.info`** 宣告列表；文档 **`grpc-services.md`**、**`compatibility.md`**；单测 **`tests/test_agent_capabilities.py`**。 |

**说明**：上表 §三 **可增强** 行 **三-11～三-13** 均已勾选（见 **[全量待办索引](#全量待办索引)**）。同类条目亦见文末 **[十三、可增强项汇总](#十三可增强项汇总)**。

**依赖**：扩展 `.proto` 后执行 `scripts/gen_proto.sh` 并全量回归；与第一节的 TLS/网关文档一并说明「版本端点是否经网关暴露」。  
**与 M2 关系**：建议在接入数据库插件、扩大 proto/行为面前完成 **P0** 项，便于灰度与混跑。

### 3.3 CHANGELOG 编写约定（与待办 [x] 文件配套执行）

- **分类**：`Added` / `Changed` / `Deprecated` / `Removed` / `Fixed` / `Security`。
- **受众**：运维与集成方优先；破坏性变更必须高亮并指向迁移小节。
- **与 PR 关系**：合并到主分支的 user-facing 变更应在同一发布周期记入 `[Unreleased]`，发版时折叠到版本号下。

---

## 四、租户、隔离与访问控制（原阶段 D）

**里程碑**：M1 · **目标**：[目标架构](../website/docs/intro/target-architecture.md) 与对象存储模型中的 **`env/tenant/job_id` 前缀** 与多客户运营；`development-design.md` 曾列为阶段一非目标，企业化需单独立项。  
**原阶段**：D

| 状态 | 优先级 | 待办项 | 说明与验收要点 |
|------|--------|--------|----------------|
| [x] | P0 | **租户模型** | `Tenant` 实体；`policies` / `jobs` / `schedules` / `artifacts` 外键 `tenant_id`；S3 键 `devault/<env>/tenants/<tenant_id>/artifacts/<job_id>/…`；HTTP 头 **`X-DeVault-Tenant-Id`** 或 **`DEVAULT_DEFAULT_TENANT_SLUG`**；迁移 **`0005`**；文档 **`website/docs/reference/tenants.md`**。 |
| [x] | P0 | **API 与 UI 作用域** | REST/UI 在 **`get_effective_tenant` / `get_effective_tenant_ui`** 解析租户后调用 **`AuthContext.ensure_tenant_access`**；跨租户 UUID 返回 **403/404**（与租户不存在统一为 404 的策略保持不变）。 |
| [x] | P1 | **RBAC** | 角色 **`admin` / `operator` / `auditor`**；**`control_plane_api_keys`**（迁移 **`0006`**，`SHA256` 存证）；写操作 **`require_write`** / 创建租户 **`require_admin`**；UI 写操作 **`require_write_ui`**；**`devault-admin create-api-key`**。文档 **`website/docs/reference/access-control.md`**。 |
| [x] | P1 | **SSO / OIDC（可选）** | **`DEVAULT_OIDC_ISSUER`** / **`DEVAULT_OIDC_AUDIENCE`** 与 JWKS 校验；角色与租户声明可配置；与静态令牌、DB 密钥链式解析。 |
| [x] | P2 | **计费与用量埋点** | Prometheus：**`devault_http_requests_total`**（`method`、`path_template`）、**`devault_billing_committed_backup_bytes_total`**（`tenant_id`，于 **`CompleteJob`** 成功备份时按 `size_bytes` 递增）。 |

**依赖**：第一节的身份模型应预留 `tenant_id` 与主体绑定。

---

## 十四、多 Agent / 多租户执行隔离与策略路由（Greenfield）

**文档位置**：为追加章节，物理上列于 **§四（租户）** 之后、**§五** 之前；**里程碑归属仍为 M1**（企业级平台能力扩展）。  
**里程碑**：M1 · **目标**：在共享控制面、多 Agent、多租户与强运维管控前提下，建立 **Agent 身份 ↔ 授权租户** 的硬边界、**策略 ↔ 执行面（Agent 或池）** 的可选绑定，以及 **路径与主机可解释、可审计** 的用户体验；降低「路径写在哪台机、谁领了作业」的心智成本。  
**排期波次**：建议 **波次 7**（见 **[排期波次与全量待办索引](#排期波次与全量待办索引)**）；可与 **波次 3～4**（网关身份、控制台）部分并行，但 **P0 隔离项** 应在对外承诺多租户 SaaS 前收口。  
**范围说明（与历史待办关系）**：本节为 **2026-05-10** 起 **追加** 条目；**不修改、不删减** §零～§九、§十～§十三 既有行文的勾选与表述。实现本节时 **不要求向后兼容**（无旧 Agent/旧策略并存约束；迁移策略由实施 PR 自定）。

### 14.1 优先级分层（实施顺序建议）

| 层级 | 主题 | 索引编号 |
|------|------|-----------|
| **P0** | 安全与隔离：注册与凭据绑定租户、`LeaseJobs` 及作业链 tenant 硬过滤、存储与元数据隔离复核、吊销与轮换 | **十四-01～十四-04**（**已收口**） |
| **P1** | 路由与策略模型：策略绑定 `agent_id` 或 `agent_pool_id`、池抽象、调度/租约/failover 语义 | **十四-05～十四-07**（**已收口**） |
| **P2** | 可观测与体验：Heartbeat 主机与 allowlist、租户范围 Agent 列表、策略表单联动校验、预检 Job、作业展示 lease + hostname 快照 | **十四-08～十四-12**（**已收口**） |
| **P3** | 运营与文档：告警与 SLO、批量/IaC、拓扑与 Quickstart | **十四-13～十四-14** 已收口；**十四-15** 待办 |
| **P1** | **Web UI 与 API 同期交付**：流程监督 + **M2** 数据库界面与 **§九** 锁波次 | **十四-16、十四-18** |
| **P2** | **Web UI 工程闸门**：OpenAPI/模板/RBAC/CHANGELOG 一致性 | **十四-17** |

### 14.2 分节待办表（与全量索引一一对应）

| 状态 | 优先级 | 待办项 | 说明与验收要点 |
|------|--------|--------|----------------|
| [x] | P0 | **Agent enrollment：租户绑定与注册换发凭据** | 表 **`agent_enrollments`**；**`PUT`/`GET /api/v1/agents/{id}/enrollment`**；**`Register`** 前必须登记；**`EdgeAgentOut.allowed_tenant_ids`**；迁移 **`0011`** + Compose 固定 **`DEVAULT_AGENT_ID`** 种子。 |
| [x] | P0 | **`LeaseJobs` 及作业全链 tenant 硬过滤** | **`_pending_candidate_ids`** 按 **`AuthContext.allowed_tenant_ids`** 过滤；**`RequestStorageGrant` / `CompleteJob` / `ReportProgress`** 调用 **`_grpc_ensure_job_tenant`**；restore READ 校验 **artifact 与 job 租户一致**。 |
| [x] | P0 | **跨租户隔离复核** | S3 键 **`tenants/<tenant_id>/artifacts`**；预签名仅作业链内对象；指标 **`devault_jobs_total`** 等已含 **`tenant_id`**；审计 **`extra.tenant_id`**（grant/complete）。与 API Key **`allowed_tenant_ids`**、登记列表语义一致（**`website/docs/admin/agent-fleet.md`**）。 |
| [x] | P0 | **凭据吊销、轮换与 Runbook** | 既有 **`revoke-grpc-sessions`**；无 **`edge_agents`** 行时凭登记仍可吊销；**`website/docs/admin/agent-credential-lifecycle.md`**（双窗轮换、泄露响应、与租约回收关系）。 |
| [x] | P1 | **策略绑定执行目标** | **`policies.bound_agent_id` / `bound_agent_pool_id`**（迁移 **`0012`** CHECK）；**`_pending_candidate_ids`** EXISTS 收窄 **LeaseJobs**；REST **`PolicyCreate`/`Patch`** + UI 策略表单。 |
| [x] | P1 | **Agent 池** | **`agent_pools`** + **`agent_pool_members`**（**`weight`/`sort_order`**）；**`GET …/agent-pools/{id}`** 返回成员 **`last_seen_at`**（**`edge_agents`**）；**`PUT …/members`** 整表替换。 |
| [x] | P1 | **调度与租约语义** | 文档 **`website/docs/admin/agent-pools.md`**：同策略 **Redis 锁**、**`lease_expires_at`** 回收 → **`pending`** 后池内他机可领；**retry** 新 **`job_id`** 可换实例；**`sort_order`/`weight`** 语义与后续加权预留说明。 |
| [x] | P2 | **Heartbeat 扩展** | 上报 **`hostname`**、**`os`**、可选 **`region`/`env`**；**允许备份路径前缀（allowlist）** 或挂载摘要；proto + 持久化字段。 |
| [x] | P2 | **租户范围 Agent 列表** | REST/UI **按租户** 展示已授权 Agent 及最近快照；与 **§六** 全平台 **`/ui/agents`** 并存或演进为租户子视图（由设计 PR 定稿）。 |
| [x] | P2 | **策略创建/编辑 UX** | 选 Agent 或池 → 展示 allowlist → 填 `paths`；服务端 **`paths` ⊆ allowlist**（或租户级「仅提示」开关）；OpenAPI 与控制台字段一致。 |
| [x] | P2 | **备份路径预检 Job** | 可选一键：Agent 校验路径存在/可读，结果写入 **`jobs.result_meta`** 或专用状态；与 **§七** 演练类 Job 区分职责。 |
| [x] | P2 | **作业详情：lease + hostname 快照** | UI/API 展示 **`lease_agent_id`** 及 **领租约或完成时固化** 的 hostname（避免事后改名导致审计不一致）。 |
| [x] | P3 | **告警与 SLO** | Agent 长期失联、策略无健康执行者、连续备份失败、策略 paths 与 allowlist 冲突；对接 **§六** Prometheus/Alertmanager。 |
| [x] | P3 | **批量注册与 IaC** | Terraform / OpenAPI 批量：Agent enrollment、池、策略；减少控制台手工。 |
| [ ] | P3 | **文档与 Quickstart** | 多租户拓扑图、密钥生命周期、池 vs 单 Agent、与「客户端 + 策略」类备份产品心智对照；更新 **`website/docs/user/quickstart.md`** 等入口。 |
| [x] | P1 | **交付节奏：§十四 后端与 Web UI（`E-UX-001`）竖切同期闭合或登记豁免** | 每个 **十四-01～十四-15** 相关 PR：**同一发布周期** 交付 **`/ui/*` 最小可用面**（与新增字段、租户作用域、危险操作确认对齐）；仅 API 时须在 PR 描述或 **`website/docs/guides/web-console.md`** 写明 **豁免原因 + UI 回填 issue/截止**；**`E-UX-001`** 与 **`E-MT-002`** 联合复盘直至无开放豁免（**十四-16**：**`CONTRIBUTING.md`**、**PR 模板**、**`guides/web-console.md`** 豁免台账已制度化）。 |
| [x] | P2 | **OpenAPI ↔ `/ui/*` 字段与 RBAC 闸门** | **`JobOut` / `PolicyOut` 等** 变更时同步 **`web/templates/`**、**`routes/ui.py`** 表单与只读列；**`auditor`** 与 **§四** 写分离一致；用户可见行为变更记入 **`CHANGELOG.md`**；**`scripts/verify_ui_openapi_registry.py`** + **CI**（**十四-17**）。 |
| [ ] | P1 | **M2：§九 数据库 MVP 的 Web UI 与 API 同期排期（波次 5 内闭合）** | **九-01～九-04** 每条须有 **向导 / 列表 / 详情 / 双重确认** 中与能力对等的最小 UI；排期绑定 **波次 5**，与 **§八** 已落地模式一致；**验收**：不在「仅 REST/CLI 可用」状态下对外宣称数据库备份 **GA**。 |

**依赖**：**§一** Register/会话模型；**§四** 租户与 RBAC；**§六** 观测与 Agent 舰队；**§八** 控制台策略表单；**`E-UX-001`**（**§八**）与 **十四-16～十八** 为 **交付节奏** 交叉依赖。可与 **§九** 数据库 MVP 并行设计 proto，但 **P0 建议先于对外多租户承诺** 交付。

### 14.3 Web UI 与 REST 同步排期（摘要）

| 索引 | 排期波次 | 要点 |
|------|----------|------|
| **十四-16** | **7**（主）、持续 | **竖切**：后端能力与 **`/ui/*`** 同期或豁免登记；**`guides/web-console.md`** 为缺口台账之一。 |
| **十四-17** | **7**（主） | **闸门**：字段、角色、变更可见性与 **OpenAPI** 对齐。 |
| **十四-18** | **5** | **M2**：**§九** 能力与控制台 **同波次闭合**，见上表 **十四-18** 行。 |

---

## 五、数据治理、加密与合规（原阶段 E）

**里程碑**：M1 · **目标**：满足常见企业安全问卷；对齐 [目标架构](../website/docs/intro/target-architecture.md) 统一存储侧的「生命周期与合规扫描」叙述。  
**原阶段**：E

| 状态 | 优先级 | 待办项 | 说明与验收要点 |
|------|--------|--------|----------------|
| [x] | P1 | **Artifact 加密（可选到默认）** | 策略 **`encrypt_artifacts`** + Agent **静态 DEK**（**`DEVAULT_ARTIFACT_ENCRYPTION_KEY`**）或 **KMS 信封**（manifest **`key_wrap=kms`**）；AES-256-GCM **`devault-chunked-v1`**；manifest **`encryption`**。见 **`website/docs/security/artifact-encryption.md`**。**可增强**：密钥轮换策略独立 Epic。 |
| [x] | P1 | **静态加密与 `encrypted` 字段真实性** | **`CompleteJob`** 读取 manifest，**`artifacts.encrypted`** 仅在为 **chunked 密文格式**（`algorithm` / `format`）时为 **true**；恢复 READ 签发 manifest 预签名供 Agent 解密。 |
| [x] | P2 | **KMS / 信封加密 / 按租户 CMK（可增强）** | **`devault.crypto.kms_envelope`**（**`GenerateDataKey`** / **`Decrypt`**）；manifest **`kms_ciphertext_blob_base64`** 等；CMK：**策略 `kms_envelope_key_id`** → **`tenants.kms_envelope_key_id`**（**`PATCH /api/v1/tenants/{id}`**）→ **`DEVAULT_KMS_ENVELOPE_KEY_ID`**；**Agent** 进程调 KMS。迁移 **`0010`**。**可增强**：DEK 目录服务、更细审计、与 HSM 集成。 |
| [x] | P3 | **默认或租户级强制加密策略** | **`DEVAULT_REQUIRE_ENCRYPTED_ARTIFACTS`**；**`tenants.require_encrypted_artifacts`**；创建/更新策略与内联备份 **`config`** 校验 **`encrypt_artifacts`**；**`CompleteJob`** 拒绝「要求加密但 manifest 非 chunked 密文」。**可增强**：审计专用例外流。 |
| [x] | P1 | **保留策略与生命周期** | 策略 **`retention_days`** → **`artifacts.retain_until`**（**`CompleteJob`**）；**`devault-scheduler`** 定时删除对象 + DB 行；指标 **`devault_retention_*`**；文档 **`website/docs/guides/retention-lifecycle.md`**。存储类过渡仍在桶侧配置。 |
| [x] | P2 | **WORM / 对象锁定（Object Lock）** | 策略 **`object_lock_mode`**（**`GOVERNANCE`** \| **`COMPLIANCE`**）与 **`object_lock_retain_days`**；**`presign_put_object`** / **`start_multipart_upload`** 携带保留截止时间（**`grpc/object_lock_params.py`**）。桶须启用 Object Lock。**可增强**：与存储侧策略引擎统一建模。 |
| [x] | P2 | **Legal Hold** | **`artifacts.legal_hold`**（迁移 **`0010`**）；**`PATCH /api/v1/artifacts/{id}/legal-hold`**（admin）；**`purge_expired_artifacts`** 跳过 **`legal_hold=true`**。**可增强**：与 S3 Bucket 级 Legal Hold 自动同步、审计导出。 |
| [x] | P2 | **BYOB（客户自带 Bucket）** | **`tenants.s3_bucket`**、**`s3_assume_role_arn`** / **`s3_assume_role_external_id`**；**`build_s3_client_for_tenant`**、**`effective_s3_bucket`**、**`get_storage_for_tenant`**；预签名、Multipart 收尾、保留清理按租户解析桶与 STS（租户角色优先）。文档 **`website/docs/reference/tenants.md`**、**`storage/sts-assume-role.md`**、**`storage/object-store-model.md`**；与 [目标架构 · 统一存储](../website/docs/intro/target-architecture.md#unified-storage-extensions) 一致。 |

---

## 六、控制面高可用、灾备与可运维性（原阶段 F）

**里程碑**：M1  
**原阶段**：F

| 状态 | 优先级 | 待办项 | 说明与验收要点 |
|------|--------|--------|----------------|
| [x] | P1 | **元数据库备份与恢复 Runbook** | PG 逻辑备份、PITR（控制面自身）；RTO/RPO 目标文档化。见 **`website/docs/install/control-plane-database-dr.md`**；脚本 **`deploy/scripts/control-plane-pg-backup.sh`** / **`control-plane-pg-restore.sh`**。 |
| [x] | P1 | **gRPC 服务多实例部署指南** | 无状态租约 + Redis 锁已部分具备；补充会话亲和性说明、水平扩缩步骤。见 **`website/docs/install/grpc-multi-instance.md`**；叠加 **`deploy/docker-compose.grpc-ha-example.yml`**、脚本 **`deploy/scripts/compose-grpc-ha-demo.sh`**。 |
| [x] | P1 | **Agent 批量管理** | 版本查询、强制升级策略、与控制面协议版本协商（`.proto` 版本号）。**`edge_agents`** 表；**`GET /api/v1/agents`**；**`LeaseJobs`** 可选二次校验 **`DEVAULT_GRPC_ENFORCE_VERSION_ON_LEASE`**；文档 **`website/docs/reference/agent-fleet.md`**。 |
| [x] | P2 | **Agent 舰队 Web UI** | 简易控制台 **`/ui/agents`**（HTTP Basic，与 API 同源数据）；导航 **`agents.html`**；展示 SemVer / proto 合规列。 |
| [x] | P2 | **Helm Chart / K8s 清单** | Chart：`deploy/helm/devault`；文档站 **`website/docs/install/kubernetes-helm.md`**；CI **`helm lint`**。Operator 可作为更后阶段。 |
| [x] | P2 | **告警路由** | Prometheus **`rule_files`** + **Alertmanager**（`deploy/alertmanager.yml`）；Compose 叠加 **`deploy/docker-compose.prometheus.yml`**（`alertdump` 演示 Webhook）；Helm **`monitoring.enabled`**；规则含备份/完整性/锁争用/保留清理；**存储配额**见云侧监控说明（`observability.md`）。 |

---

## 七、备份验证与持续信任（原阶段 G）

**里程碑**：M1  
**原阶段**：G

| 状态 | 优先级 | 待办项 | 说明与验收要点 |
|------|--------|--------|----------------|
| [x] | P1 | **自动恢复演练 Job** | **`restore_drill`** Job + **`restore_drill_schedules`** Cron；Agent 解压至 **`drill_base_path`/devault-drill-`<job_id>`/**，`.devault-drill-report.json` + **`CompleteJob.result_summary_json`** → **`jobs.result_meta`**；API **`POST /jobs/restore-drill`**、**`/restore-drill-schedules`**；**Web UI**：**`/ui/restore-drill-schedules`**、Jobs 列表演练路径摘要（Artifacts 仅手动恢复）；文档 **`website/docs/guides/restore-drill.md`**、**`guides/web-console.md`**。 |
| [x] | P1 | **备份完整性告警** | **`devault_jobs_total`** 扩展 **`tenant_id` / `policy_id` / `error_class`**；**`devault_backup_integrity_control_rejects_total`**（控制面 CompleteJob 拒绝）；**`devault_jobs_overdue_nonterminal`**（**`DEVAULT_JOB_STUCK_THRESHOLD_SECONDS`**）；示例规则 **`deploy/prometheus/alerts.yml`** + **`prometheus.yml` `rule_files`**；文档 **`website/docs/install/observability.md`**。 |
| [ ] | P2 | **增量与时间线（长期）** | WAL/binlog、PITR（`development-design.md` §3.4 非目标）；单独 Epic，依赖数据库插件成熟。 |

---

## 八、文档与对外形态（原阶段 H）

**里程碑**：M1  
**原阶段**：H

| 状态 | 优先级 | 待办项 | 说明与验收要点 |
|------|--------|--------|----------------|
| [x] | P1 | **企业部署参考架构** | 文档站 **`website/docs/install/enterprise-reference-architecture.md`**（Mermaid：DMZ、网关、VPC、对象存储、出站）；与 **`intro/target-architecture.md`**、**`intro/architecture-overview.md`** 互链。 |
| [x] | P1 | **安全白皮书摘要** | **`website/docs/security/security-whitepaper.md`**：信任边界、密钥流、审计、gRPC 指标告警引用；**§五** KMS/信封、强制加密、Object Lock、Legal Hold、BYOB 已实现（见 **`artifact-encryption.md`** 等），白皮书中若有「未实现」列表宜与 backlog **§五** / **§九** / **§七** 同步校对。 |
| [x] | P2 | **`docs/README.md` 与实现差距表** | 仓库 **`docs/README.md`**：对照 **`docs-old/README.md`** 愿景条目的实现状态表与站内链接。 |
| [x] | P1 | **Web UI：策略表单与备份配置对齐（KMS / Object Lock / 文案）** | 已实现：**`policy_form.html`**、**`POST /ui/policies/*`** 经 **`_file_backup_config_v1`** 写入 **`kms_envelope_key_id`**、**`object_lock_mode` / `object_lock_retain_days`**（与 **`FileBackupConfigV1`**、REST 一致）；加密说明链 **`artifact-encryption.md`** 语境。 |
| [x] | P1 | **Web UI：租户运维（列表 / PATCH BYOB·合规字段；Admin）** | 已实现：**`/ui/tenants`**、**`/ui/tenants/new`**、**`/ui/tenants/{id}/edit`**（**`require_admin_ui`**），对接 **`TenantCreate` / `TenantPatch`** 与 **`control_svc`**（BYOB、**`require_encrypted_artifacts`**、KMS 等）。 |
| [x] | P1 | **Web UI：租户上下文与切换（多租户日常不设 curl）** | 已实现：**HttpOnly Cookie** **`devault_ui_tenant`**（**`UI_TENANT_COOKIE`**，path `/ui`），**`get_effective_tenant_ui`**（Cookie → **`X-DeVault-Tenant-Id`** → 默认 slug）；**`POST /ui/context/tenant`**；导航下拉与 **`tenants_for_switcher_nav`**。验收路径：**`/ui/jobs`**、**`/policies`**、**`/artifacts`** 等与 REST 租户一致。**可增强**：书签深链带 `tenant` query。 |
| [x] | P2 | **Web UI：Artifacts 列补齐（encrypted / legal_hold）** | 已实现：**`artifacts.html`** 列 **`Encrypted`**、**`Legal hold`**；数据与 **`Artifact`** / **`ArtifactOut`** 对齐。 |
| [x] | P2 | **Web UI：法务保留 Legal Hold（Admin 行操作 + 确认）** | 已实现：**`POST /ui/artifacts/{id}/legal-hold`**（**`require_admin_ui`**）→ **`control_svc.patch_artifact_legal_hold`**；行内表单 + 浏览器 **`confirm()`**；非 admin 无操作列。 |
| [x] | P3 | **Web UI：运维快捷键（吊销会话、密钥/CLI 文档入口）** | 已实现：**`/ui/agents`** **Admin**：**`POST /ui/agents/{id}/revoke-grpc-sessions`** → **`revoke_all_grpc_sessions_for_agent`**；muted 文案链 **`website/docs/reference/access-control.md`**、**`website/docs/security/api-access.md`**。**可增强**：密钥列表脱敏预览（只读 REST）。 |

---

# 里程碑 M2：新备份类型与产品设计对齐

---

## 九、`development-design.md` 数据库与产品差距补全（原阶段 C）

**里程碑**：M2 · **目标**：完成已承诺的**数据库备份 MVP**，并关闭设计文档与实现之间的已知差距；在 **M1 平台能力**就绪后集中交付。  
**原阶段**：C

| 状态 | 优先级 | 待办项 | 说明与验收要点 |
|------|--------|--------|----------------|
| [ ] | P0 | **`postgres` 插件（Agent 可执行）** | `pg_dump`（或选定默认格式）；manifest 含引擎版本与工具版本；与现有 Job/Artifact/租约模型一致。 |
| [ ] | P0 | **`mysql` 插件（Agent 可执行）** | `mysqldump` / `mariadb-dump` 与镜像版本矩阵；参数标准化（如 `--single-transaction` 等可配置）。 |
| [ ] | P0 | **Policy `type` / 配置校验扩展** | API 与 DB 层对数据库类 policy 的校验、敏感字段不落日志。 |
| [ ] | P0 | **数据库恢复流程与危险操作确认** | UI/CLI/API 双重确认、文档化步骤；与文件恢复类似的「非空目录确认」策略。 |
| [ ] | P1 | **集成测试矩阵（最小版本组合）** | 文档 20.3 与 21 节：选 1～2 组 PG/MySQL 版本在 CI 或夜间流水线跑通。 |
| [ ] | P1 | **更新 `development-design.md` 目录结构描述** | 文档仍写 `Celery worker` 包路径；需与当前「Agent + 无 Celery」结构对齐，避免新成员误读。 |
| [ ] | P2 | **验收清单 22 节全部勾选** | 15 分钟首次备份、错误可见性、限制与 roadmap 链接等（见设计文档 §22）。 |

**依赖**：M1 第二节对大 dump 的 **Multipart** 与（强烈建议）**跨重启续传** 应已落地或并行关闭，否则企业库备份易失败；M1 第三节 **双端版本与兼容** 建议在插件与 proto 扩展前到位。

---

## 十、建议的 Epic 映射（便于项目管理）

| Epic ID | 名称 | 里程碑 | 主要覆盖（原阶段） |
|---------|------|--------|-------------------|
| E-ARCH-001 | 传输安全与网关 | M1 | A |
| E-DATA-001 | 大对象与续传（Multipart + 流式） | M1 | B（已完成主线） |
| E-DATA-002 | Multipart 跨重启续传 + STS 临时凭证 | M1 | B（续传与 STS AssumeRole 均已交付） |
| E-VER-001 | 版本、双端兼容与 CHANGELOG | M1 | I |
| E-MT-001 | 租户与 RBAC | M1 | D |
| E-GOV-001 | 加密、保留、合规 | M1 | E |
| E-OPS-001 | HA、DR、K8s、告警 | M1 | F |
| E-TRUST-001 | 验证与演练 | M1 | G |
| E-DOC-001 | 企业文档 | M1 | H |
| E-UX-001 | Web 控制台与 REST 对等 | M1 | H（扩充）+ **§十四 · 十四-16～十七**（同步排期闸门）+ **十四-18**（M2 与 §九 同期） |
| E-DB-001 | 数据库备份 MVP | M2 | C |
| E-MT-002 | 多 Agent 租户隔离与策略执行路由（Greenfield） | M1 | §十四（与 D/F/H 交叉） |

**Epic → 排期波次**（与 **[排期波次与全量待办索引](#排期波次与全量待办索引)** 一致）：**E-OPS-001** 中 **Helm / K8s** 与 **告警路由（Prometheus + Alertmanager）** 已交付；**`E-DATA-001` / `E-DATA-002`** 之 **§二 Multipart×加密** 已交付；**E-VER-001** 之 **§三** 可增强（**三-11～三-13**）已交付 → **波次 2** 版本与韧性主线已收敛；**E-ARCH-001** 之 **§一** 可增强（**一-08 Envoy `local_rate_limit`**、**一-09 Agent Redis 会话 / 吊销**）已交付 → **波次 3** 网关与身份演进主线已收敛；**E-GOV-001** 之 **KMS、强制加密、WORM、Legal Hold、BYOB**（迁移 **`0010`**）→ **波次 4** **已交付**。**`E-UX-001`**（**§八 · 八-04～八-09**）→ **波次 4** **已交付**：控制台与 **REST** 对等（策略 KMS/Object Lock、租户运维与 Cookie 切换、Artifacts 列与 Legal Hold、Agent gRPC 会话吊销等）；实现见 **`src/devault/api/routes/ui.py`**、**`deps.py`**、**`web/templates/`**；文档维护 **`website/docs/guides/web-console.md`** 与 **E-DOC-001**。

**`E-DB-001`** → **波次 5**（与 **`E-UX-001` · 十四-18**：§九 **API + Web UI** 同期闭合）；**E-TRUST-001** 之 **§七 增量与时间线** → **波次 6**。**`E-MT-002`**（**§十四 · 十四-15～十七**；**十四-01～十四-14** 已收口）→ **波次 7**（与 **波次 3～4** 可部分并行，见 **§十四** 首段）；**`E-UX-001` · 十四-16～十七** 与 **波次 7** 同一闭环监督。其余 Epic 主线条目在当前仓库已为 `[x]`。

---

## 十一、重组对照表（旧「阶段字母」→ 新章节）

| 原阶段 | 新位置 |
|--------|--------|
| A | M1 · 一、传输、身份与入口 |
| B | M1 · 二、数据面可靠性 |
| I | M1 · 三、版本管理 |
| D | M1 · 四、租户与访问控制 |
| E | M1 · 五、数据治理与合规 |
| F | M1 · 六、高可用与运维 |
| G | M1 · 七、备份验证与信任 |
| H | M1 · 八、文档与对外形态 |
| C | M2 · 九、数据库与产品差距补全 |
| （追加） | M1 · **十四、多 Agent / 多租户执行隔离与策略路由**（Greenfield；**正文**紧接 **§四**、在 **§五** 之前；索引 **十四-01～十四-18** 紧接 **四-05** 之后；**十四-16～十八** 为 **Web UI 与 REST 同步排期**） |

---

## 十二、修订记录

| 日期 | 变更 |
|------|------|
| 2026-05-08 | 初稿：基于 `development-design.md`、目标架构文档与当前代码实现整理企业级待办清单。 |
| 2026-05-08 | 新增阶段 I：版本管理、控制面/Agent 双端校验、CHANGELOG 约定；Epic `E-VER-001`；基线补充版本号现状。 |
| 2026-05-08 | **阶段 A 落地**：TLS/mTLS、Envoy 示例、限流与审计、`Register`、Health、`GET /version`、[`grpc-tls.md`](./grpc-tls.md)；发布 **0.2.0**。 |
| 2026-05-08 | **阶段 B（P0/P1）落地**：S3 Multipart、分片上传重试、流式恢复、单 PUT 流式上传；[`s3-data-plane.md`](./s3-data-plane.md)；发布 **0.3.0**（STS 仍为待办）。 |
| 2026-05-08 | 阶段 B 表拆分为「同进程重试」[x] 与显式待办：**跨重启 Multipart 续传** [ ]、**STS/AssumeRole** [ ]；新增 Epic **E-DATA-002**。 |
| 2026-05-08 | **重组**：引入里程碑 **M1（平台）/ M2（数据库备份）**；原阶段 C 移至 M2；原 A/B/D/E/F/G/H/I 归入 M1 并重新编号章节；新增实施路线说明、Epic「里程碑」列、重组对照表；基线表述与第三节 `GET /version` 说明对齐现状。 |
| 2026-05-08 | **M1·二 P1**：Multipart **跨重启/跨进程续传** 落地（proto、`jobs.bundle_wip_*`、ListParts 补签、Agent checkpoint、Prometheus）；发布 **0.4.0**；`E-DATA-002` 中续传子项完成，STS 仍为待办。 |
| 2026-05-09 | **M1·三 P0**：**SSOT 与发版脚本**（`pyproject.toml`、metadata 回退、`scripts/bump_release.py` / `verify_release_docs.py`、pytest、`ci.yml`）；文档站「发版与变更记录」更新。 |
| 2026-05-09 | **M1·三 P0/P1**：**gRPC 双端版本协商**（`proto/agent.proto`、`agent_version`、审计 extra）；**HTTP `/version`** 扩展；**`--version`** 三入口；配置与 gRPC 参考文档更新。 |
| 2026-05-09 | **M1·三**：**`docs/compatibility.json`**、**`docs/RELEASE.md`**、**`verify_compatibility_matrix.py`**、CI **`matrix.suite`**、**`server_capabilities`**（proto + `server_capabilities.py`）、manifest **`devault_release` / `grpc_proto_package`**；**`website/docs/development/compatibility.md`**。 |
| 2026-05-09 | §3.2 增补 **可增强** 待办：多版本镜像 E2E CI、**`bump_release`** 与 **`compatibility.json`** 联动、Agent **`server_capabilities`** 降级路径（均为 `[ ]`）。 |
| 2026-05-09 | **M1·二 P2**：控制面 **STS / AssumeRole** 访问 S3（`s3_client.py`、配置项、单测）；文档站 **`storage/sts-assume-role.md`**；**`docs-old/s3-data-plane.md`** 与 **`enterprise-backlog.md`** 对应行勾选。 |
| 2026-05-09 | **M1·四 P0**：**租户模型**落地（`tenants` 表、各资源 `tenant_id`、默认租户种子、幂等键按租户唯一、**`GET/POST /api/v1/tenants`**、对象键含租户段、Lease `config_json` 含 **`tenant_id`**）；文档 **`reference/tenants.md`** 及配置/API/对象存储说明更新。 |
| 2026-05-09 | **M1·四**：**API/UI 作用域强化**、**RBAC**（`control_plane_api_keys` + 三角色）、**可选 OIDC JWT**、**计费向 Prometheus**（HTTP 计数 + 备份提交字节）；**`devault-admin`** CLI；文档 **`reference/access-control.md`** 与配置/安全页更新。 |
| 2026-05-09 | **M1·五 P1**：**Artifact AES-GCM 静态加密**（策略 **`encrypt_artifacts`**、Agent 密钥、分块 **`devault-chunked-v1`**、manifest / **`artifacts.encrypted`**、恢复 manifest 预签名）；文档 **`website/docs/security/artifact-encryption.md`**；**`CHANGELOG`**。 |
| 2026-05-09 | **可增强项显式化**：**§一** 增加 Envoy **`local_rate_limit`**、Register 令牌演进；**§二** 增加 Multipart×加密联调；**§五** 增加 KMS/信封、强制加密策略；**「如何使用」** 增加 **可增强** 列说明；文末新增 **§十三、可增强项汇总**（与 §三.2 三项互链）。 |
| 2026-05-09 | **M1·五 P1**：**保留策略与生命周期**（**`retention_days`**、**`retain_until`**、scheduler 清理、存储 **`delete_object`**、Compose scheduler **S3** 环境、`ArtifactOut` / UI）；文档 **`guides/retention-lifecycle.md`**、**`CHANGELOG`**。 |
| 2026-05-09 | **M1·六 P1**：**控制面元数据库备份与灾难恢复 Runbook**（逻辑备份/PITR 概要/RTO·RPO 表、`deploy/scripts/control-plane-pg-*.sh`）；文档 **`website/docs/install/control-plane-database-dr.md`**；侧栏与 **`backup-and-restore.md`** 互链。 |
| 2026-05-09 | **M1·六 P1**：**gRPC/API 多实例部署指南**（Redis 锁与 PG 租约、scheduler 单副本、进程内限流语义、Envoy ROUND_ROBIN、Compose 端口与 `--scale`）；**`deploy/docker-compose.grpc-ha-example.yml`**、**`deploy/scripts/compose-grpc-ha-demo.sh`**；**`docs-old/grpc-tls.md`** 增加 §9 互链。 |
| 2026-05-09 | **M1·六 P1**：**Agent 批量管理**：迁移 **`edge_agents`**；Heartbeat/Register 写入；**`LeaseJobs`** 持久化版本门闸；**`GET /api/v1/agents`**、CLI **`devault agent list`**；**`website/docs/reference/agent-fleet.md`**、配置 **`DEVAULT_GRPC_ENFORCE_VERSION_ON_LEASE`**。 |
| 2026-05-09 | **M1·六 P2**：**Agent 舰队 Web UI**：**`/ui/agents`**、**`agents.html`**、**`api/presenters.py`**（**`edge_agent_to_out`** 与 REST 共用）；待办清单与 **`guides/web-console.md`** 更新。 |
| 2026-05-09 | **M1·七 P1**：**自动恢复演练**：**`JobKind.restore_drill`**、迁移 **`0008`**、**`CompleteJobRequest.result_summary_json`**；调度器 **`rd_*`** Cron；文档 **`guides/restore-drill.md`**。 |
| 2026-05-09 | **M1·七**：恢复演练 **Web UI**（**`/ui/restore-drill-schedules`**、Jobs 演练摘要列；Artifacts 仅手动恢复）。 |
| 2026-05-09 | **M1·七 P1**：**备份完整性告警**：指标扩展与 **`deploy/prometheus/alerts.yml`**；**`stuck_jobs_collector`**；配置 **`DEVAULT_JOB_STUCK_THRESHOLD_SECONDS`**。**M1·八**：**企业部署参考架构**、**安全白皮书摘要**、**`docs/README.md`** 差距表；侧栏与可观测性文档更新。 |
| 2026-05-09 | **文档**：**`website/docs/intro/target-architecture.md`** 承接原 **`docs-old/target-architecture.md`** 正文；旧文件改为迁移占位；全站引用改为文档站内链；**`observability.md`** 使用 HTML 标题锚点以兼容 MDX。 |
| 2026-05-09 | **清单重组**：新增 **排期波次（1～6）**、**全量待办索引**（§零～§九 + §三.3 注，共 73 行，与分节表一一对应）；**整体实施路线** 补充排期原则；**如何使用** 增加「排期波次」列说明；**§十** 增加 Epic→波次映射；**§十三** 与全量索引互链。（**注**：后续 **§十四** 追加后索引行数递增，以当前 **[全量待办索引](#排期波次与全量待办索引)** 为准。） |
| 2026-05-09 | **M1·六 P2**：**Helm Chart** 落地（`deploy/helm/devault`、CI `helm lint`、文档 **`website/docs/install/kubernetes-helm.md`**）；**§六** 与全量索引 **六-05** 勾选；**波次 1** 表更新。 |
| 2026-05-09 | **M1·六 P2**：**告警路由** 落地（`deploy/alertmanager.yml`、`deploy/docker-compose.prometheus.yml` 扩展、**`deploy/prometheus/alerts.yml`** 增补策略锁/保留清理；Helm **`templates/monitoring.yaml`** + **`prometheus-alerts.yml`**；**`website/docs/install/observability.md`** 重写 Alertmanager 章节；**§六** 与全量索引 **六-06** 勾选；**波次 1** 标为已收敛）。 |
| 2026-05-09 | **M1·二 P3**：**Multipart×Artifact 加密** 联调落地（Agent **`multipart_resume`** 校验、checkpoint **`encrypt_artifacts`**、**`devault_multipart_encrypted_mpu_completes_total`**、文档与单测；**§二**、全量索引 **二-07**、**§十三**、**波次 2** 表更新）。 |
| 2026-05-09 | **M1·三 P2**：**CI 多版本镜像 E2E 矩阵**（**`e2e-version-matrix.yml`**、**`ci_e2e`** / **`matrix_definitions`**、Compose override、gRPC 冒烟脚本、**`verify_compatibility_matrix`** 扩展、**`compatibility.md`**；全量索引 **三-11**、**§三.2**、**§十三**、**波次 2** 表更新）。 |
| 2026-05-09 | **M1·三 P3**：**`bump_release` ↔ `compatibility.json`**（**`sync_compatibility_current_release`**、文档与单测）；**Agent `server_capabilities` 降级**（**`gate_multipart_*`**、**`AgentCapabilityState`**、全量索引 **三-12 / 三-13**、**§十三**、**波次 2** 收敛）。 |
| 2026-05-09 | **M1·一 P3**：**Envoy `local_rate_limit`**（**`deploy/envoy/envoy-grpc-tls.yaml`**）；**Register → Redis 每 Agent 会话**（**`agent_grpc_session`**、**`revoke-grpc-sessions`**、**`_require_agent_bearer_matches`**）；全量索引 **一-08 / 一-09**、**§十三**、**波次 3** 收敛。 |
| 2026-05-09 | **M1·八**：**Web UI 与 REST 对等落地** — 全量索引 **八-04～八-09**、**§八** 分节表勾选 **`[x]`**；**`deps.py`**：**`UI_TENANT_COOKIE`**、**`get_effective_tenant_ui`**、**`tenants_for_switcher_nav`**、**`require_admin_ui`**；**`routes/ui.py`**（策略 KMS·Object Lock、**`/ui/tenants`**、**`POST /ui/context/tenant`**、Artifacts 列与 Legal Hold **`confirm()`**、**`/ui/agents/.../revoke-grpc-sessions`**）；**§十 `E-UX-001`** / **波次 4** 标为 **已交付**。**`guides/web-console.md`** 宜同步复核。 |
| 2026-05-10 | **§十四 追加（Greenfield）**：**多 Agent / 多租户执行隔离与策略路由** 待办 **十四-01～十四-15**（P0～P3）；**全量待办索引** 增行；**排期波次** 增 **波次 7**；**Epic `E-MT-002`**；**重组对照表** 增「§十四」行。**说明**：本节实现 **不要求向后兼容**；**不增删、不改写** §零～§九 及既有 Epic/历史待办正文与勾选。 |
| 2026-05-10 | **§十四 位置调整**：分节正文移至 **§四（租户）** 之后、**§五** 之前；**全量待办索引** 中 **十四-01～十四-15** 移至 **四-05** 与 **五-01** 之间；**§十四 · 文档位置** 与 **§十一 · 重组对照表** 表述已同步。 |
| 2026-05-10 | **Web UI 同步排期入册**：新增 **十四-16～十四-18**（竖切同期、`OpenAPI↔UI` 闸门、**M2·§九** 与 UI **波次 5** 绑定）；**整体实施路线**、**如何使用**、**波次 5/7**、**§十四 · 14.1～14.3**、**`E-UX-001`/`E-DB-001`/`E-MT-002`** 说明与 **§十三** 互链已更新。 |
| 2026-05-11 | **M1·五 P2/P3**：**KMS 信封**（manifest **`key_wrap=kms`**、Agent KMS API）、**强制加密**（**`DEVAULT_REQUIRE_ENCRYPTED_ARTIFACTS`** / **`require_encrypted_artifacts`**、`CompleteJob` 校验）、**Object Lock**、**Legal Hold**、**BYOB**（租户桶 + STS）；迁移 **`0010`**。**§五** 分节表、**全量索引** **五-03～五-08**、**§十三** 与本文件 **§十 Epic→波次 4** 与实现 **`[x]`** 对齐；文档站 **配置 / artifact-encryption / tenants / retention / object-store / sts-assume-role** 等同步。 |
| 2026-05-11 | **M1·八（规划立项）**：拟定全量索引 **八-04～八-09** 与 **§八** / **`E-UX-001`** 范围；**勾选与实现** 见上表 **2026-05-09 · M1·八 Web UI 落地** 行（及当时代码与模板）。 |
| 2026-05-10 | **§十四 P0 收口**：**十四-01～十四-04** 落地 — **`agent_enrollments`**（迁移 **`0011`**）、**`PUT`/`GET .../enrollment`**、**`Register`** 门禁、**`LeaseJobs`** 与存储/完成链 **tenant** 硬过滤、gRPC 审计 **`tenant_id`**、restore artifact 租户校验、**`website/docs/admin/agent-credential-lifecycle.md`** 与 **agent-fleet** / **quickstart** / **grpc-services** 更新；Compose **`DEVAULT_AGENT_ID`**；**`scripts/e2e_grpc_register_heartbeat.py`** 默认 Agent UUID。 |
| 2026-05-10 | **§十四 P1 收口**：**十四-05～十四-07** — **`agent_pools`/`agent_pool_members`**、**`policies` 绑定列**（迁移 **`0012`**）、**`LeaseJobs`** SQL 绑定过滤、**`/api/v1/agent-pools`**、UI **`/ui/agent-pools`** 与策略表单、**`website/docs/admin/agent-pools.md`** 与 ER 图说明。 |

---

## 十三、可增强项汇总

**非阻塞、可后续排期。** 以下与上文 **`（可增强）`** 或 **已勾选行内「可增强」表述**对应，便于**单独 Epic / 季度排期**；实现后可在**归属章节**、**[全量待办索引](#全量待办索引)** 与下表同步勾选。

**说明**：**§五** 主线（KMS/强制加密/WORM/Legal Hold/BYOB）已在 **§五分节表** 与 **全量索引** **`[x]`**；本表 **`[x]`** 行对应「主线已交付 + 可增强子项仍见 §五分节该行说明」。**§七** 增量时间线、**§九** 数据库 MVP、**§十四** Agent 租户与路由及 **十四-16～十八（Web UI 同步）** 等待办不在本汇总表逐项展开；排期仍以 **[全量索引](#排期波次与全量待办索引)** 为准。

| 状态 | 优先级 | 归属 | 待办项 | 说明与验收要点 |
|------|--------|------|--------|----------------|
| [x] | P3 | §一 | **Envoy local_rate_limit** | 见 **§一** 表；**`envoy-grpc-tls.yaml`**。 |
| [x] | P3 | §一 | **Register → 每 Agent 令牌 / 吊销 / Redis** | 见 **§一** 表；**`agent_grpc_session`**、撤销 API。 |
| [x] | P3 | §二 | **Multipart × 加密联调** | 见 **§二** 表；已实现校验、指标与文档互链。 |
| [x] | P2 | §三.2 | **CI 多版本镜像 E2E 矩阵** | **`.github/workflows/e2e-version-matrix.yml`**、`ci_e2e`、`e2e_grpc_register_heartbeat.py`；与 **`matrices`** 互链见 **`matrix_definitions`**。 |
| [x] | P3 | §三.2 | **bump_release ↔ compatibility.json** | **`sync_compatibility_current_release`**；见 §三.2 表与 **`releasing.md`**。 |
| [x] | P3 | §三.2 | **Agent 按 server_capabilities 降级** | **`multipart_resume`** / **`multipart_upload`** 门控；见 **`grpc-services.md`**。 |
| [x] | P2 | §五 | **KMS / 信封 / 租户 CMK** | 主线已交付，见 **§五** 表；**可增强**见该行正文。 |
| [x] | P3 | §五 | **默认或租户级强制加密** | 主线已交付，见 **§五** 表；**可增强**见该行正文。 |
| [x] | P2 | §五 | **WORM / Object Lock** | 主线已交付，见 **§五** 表。 |
| [x] | P2 | §五 | **Legal Hold** | 主线已交付，见 **§五** 表。 |
| [x] | P2 | §五 | **BYOB** | 主线已交付，见 **§五** 表。 |
