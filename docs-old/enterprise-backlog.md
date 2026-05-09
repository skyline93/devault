# DeVault 企业级落地待办清单

> **文档目的**：在 [`development-design.md`](./development-design.md) 与 [**目标架构（文档站）**](../website/docs/intro/target-architecture.md) 之上，结合当前代码实现，列出使项目**可长期作为企业级备份方案**交付所需的完整待办项，便于排期、分工与验收。  
> **基线说明（截至文档编写时的实现）**：S1/S2 文件备份主路径已落地；执行单元为**边缘 Agent（Pull + gRPC 租约）**，Celery Worker 已移除；控制面为 FastAPI + 内嵌 gRPC + APScheduler + PostgreSQL + Redis；对象存储以 **S3 兼容 + 预签名 URL** 为主路径；`development-design.md` 第 20 节中 **S3 数据库 MVP 仍为未完成**。  
> **索引**：**§零～§九** 每一条（含已完成）的**不删减**汇总见 **[排期波次与全量待办索引](#排期波次与全量待办索引)**（位于 **§零** 之后）；维护时请与分节表同步勾选。

---

## 如何使用本文档

| 列 | 含义 |
|----|------|
| **里程碑** | **M1** = 平台与企业级能力（建议优先）；**M2** = 在 M1 达标后接入的**新备份类型**（数据库 MVP 等）。 |
| **优先级** | P0：安全与架构底线；P1：可靠性/规模；P2：功能扩展；P3：合规与运营增强。 |
| **依赖** | 实施前建议满足的前置项（见各节末）。 |
| **原阶段字母** | 历史编号（A～I），见文末「重组对照表」，便于与旧讨论、Epic 对齐。 |
| **可增强** | 已交付主线之上的**后续增强**；表中 **`（可增强）`** 或文末 **[十三、可增强项汇总](#十三可增强项汇总)** 所列条目**不阻塞**当前里程碑，可单独排期。 |
| **排期波次** | 跨章节的建议实施顺序（**1**～**6**），与 **P0～P3** 独立；定义见 **[排期波次与全量待办索引](#排期波次与全量待办索引)**。 |

完成某项后，可将 `[ ]` 改为 `[x]`，并在 **归属分节表**、**全量待办索引** 与 PR / 修订记录中注明。

---

## 整体实施路线（先平台、后数据库）

**策略**：优先完成 **M1 企业级平台能力**（传输与身份、数据面可靠性、版本与兼容、租户与治理、运维与信任、对外文档），再在稳定平台上接入 **M2 数据库备份** 等新产品能力。  
**原因简述**：数据库 dump 体积大、耗时长，会放大弱网、断点续传、租约与升级兼容等问题；平台能力与其正交，先夯实可减少返工。  
**不删减原则**：下文各表合起来即为**完整**待办集合；仅调整阅读顺序与里程碑归属，**不删除**重组前已计划的条目。  
**排期原则（2026-05-09 起）**：在 **M1 波次 1～2**（基础设施闭环 + 发布/数据面韧性）未收敛前，**默认不启动 M2（§九）**；§七「增量与时间线」绑定 M2，随 **波次 6** 处理。

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
| **2** | 发布工程与数据面韧性 | §二 Multipart×Artifact 加密联调；§三 CI 多版本镜像 E2E；§三 bump_release ↔ compatibility.json；§三 Agent server_capabilities 降级 |
| **3** | 网关与身份演进 | §一 Envoy local_rate_limit；§一 Register 每 Agent 令牌 / 吊销 / Redis |
| **4** | 合规与统一存储扩展 | §五 KMS / 信封 / 租户 DEK；§五 默认或租户级强制加密；§五 WORM；§五 Legal Hold；§五 BYOB |
| **5** | M2 数据库备份 MVP | §九 全部未完成项（建议在 **波次 1～2** 收敛后再启动） |
| **6** | 长期（依赖 M2） | §七 增量与时间线 |
| **—** | 已完成 | 全量索引中状态 `[x]` 的条目及 **§零** 基线 11 条 |

### 全量待办索引

（按章节顺序，与 **§零～§九** 分节表 **一一对应**，不删减。）

维护约定：**勾选状态**以 **§零～§九** 分节表为准；完成某项后请在本索引与归属分节表 **同步**更新 `[ ]` / `[x]`。

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
| 一-08 | §一 | [ ] | P3 | 3 | **Envoy 网关 local_rate_limit（可增强）** |
| 一-09 | §一 | [ ] | P3 | 3 | **Register 后续：每 Agent 令牌 / 吊销 / Redis 会话（可增强）** |
| 二-01 | §二 | [x] | P0 | — | **S3 分块上传（Multipart）** |
| 二-02 | §二 | [x] | P0 | — | **分片上传同进程重试** |
| 二-03 | §二 | [x] | P1 | — | **Multipart 跨重启 / 跨进程断点续传** |
| 二-04 | §二 | [x] | P1 | — | **恢复侧大文件流式下载** |
| 二-05 | §二 | [x] | P1 | — | **预签名权限最小化** |
| 二-06 | §二 | [x] | P2 | — | **STS / AssumeRole 临时凭证（控制面 → S3）** |
| 二-07 | §二 | [ ] | P3 | 2 | **Multipart 与 Artifact 加密的联调与边界（可增强）** |
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
| 三-11 | §三 | [ ] | P2 | 2 | **CI：多版本镜像端到端矩阵（可增强）** |
| 三-12 | §三 | [ ] | P3 | 2 | **发版脚本与 compatibility.json 联动（可增强）** |
| 三-13 | §三 | [ ] | P3 | 2 | **Agent 基于 server_capabilities 的降级路径（可增强）** |
| 三-注 | §三.3 | — | — | — | **CHANGELOG 编写约定**（持续执行流程，非 `[ ]` 勾选项；见 **§三.3**） |
| 四-01 | §四 | [x] | P0 | — | **租户模型** |
| 四-02 | §四 | [x] | P0 | — | **API 与 UI 作用域** |
| 四-03 | §四 | [x] | P1 | — | **RBAC** |
| 四-04 | §四 | [x] | P1 | — | **SSO / OIDC（可选）** |
| 四-05 | §四 | [x] | P2 | — | **计费与用量埋点** |
| 五-01 | §五 | [x] | P1 | — | **Artifact 加密（可选到默认）** |
| 五-02 | §五 | [x] | P1 | — | **静态加密与 `encrypted` 字段真实性** |
| 五-03 | §五 | [ ] | P2 | 4 | **KMS / 信封加密 / 按租户 DEK（可增强）** |
| 五-04 | §五 | [ ] | P3 | 4 | **默认或租户级强制加密策略（可增强）** |
| 五-05 | §五 | [x] | P1 | — | **保留策略与生命周期** |
| 五-06 | §五 | [ ] | P2 | 4 | **WORM / 对象锁定（Object Lock）** |
| 五-07 | §五 | [ ] | P2 | 4 | **Legal Hold** |
| 五-08 | §五 | [ ] | P2 | 4 | **BYOB（客户自带 Bucket）** |
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
| 九-01 | §九 | [ ] | P0 | 5 | **`postgres` 插件（Agent 可执行）** |
| 九-02 | §九 | [ ] | P0 | 5 | **`mysql` 插件（Agent 可执行）** |
| 九-03 | §九 | [ ] | P0 | 5 | **Policy `type` / 配置校验扩展** |
| 九-04 | §九 | [ ] | P0 | 5 | **数据库恢复流程与危险操作确认** |
| 九-05 | §九 | [ ] | P1 | 5 | **集成测试矩阵（最小版本组合）** |
| 九-06 | §九 | [ ] | P1 | 5 | **更新 `development-design.md` 目录结构描述** |
| 九-07 | §九 | [ ] | P2 | 5 | **验收清单 22 节全部勾选** |

**排期列**：`—` 表示已完成或不适用；**1～6** 为建议实施波次，含义见本节首段 **排期波次** 表。

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
| [x] | P1 | **Register / 令牌模型（相对共享 API Token）** | **`Register` RPC**：`DEVAULT_GRPC_REGISTRATION_SECRET` 换取当前 `DEVAULT_API_TOKEN`（引导式）；**每 Agent 短期令牌 / 吊销列表 / Redis 会话**仍为后续增强。 |
| [x] | P1 | **mTLS（可选但建议产品化）** | 控制面 **`DEVAULT_GRPC_SERVER_TLS_CLIENT_CA_PATH`** 要求客户端证书；Agent **`DEVAULT_GRPC_TLS_CLIENT_*`**；Envoy 侧校验见 `docs/grpc-tls.md` 演进说明。 |
| [x] | P2 | **gRPC 健康检查与就绪探针** | 注册 **`grpc.health.v1.Health`**（`""` 与 `devault.agent.v1.AgentControl` 均为 SERVING）；文档给出 `grpc_health_probe` 示例。 |
| [ ] | P3 | **Envoy 网关 local_rate_limit（可增强）** | 在现有 Envoy 示例上增加 **`local_rate_limit`** filter（或等价），与控制面每 peer 令牌桶形成**双层**限流；矩阵与默认值文档化。 |
| [ ] | P3 | **Register 后续：每 Agent 令牌 / 吊销 / Redis 会话（可增强）** | 当前 Register 仍换取**共享** `DEVAULT_API_TOKEN` 语义；后续可演进为**短期 Agent 令牌**、控制面**吊销列表**、Redis **会话绑定**，与审计字段对齐。 |

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
| [ ] | P3 | **Multipart 与 Artifact 加密的联调与边界（可增强）** | 大对象 **Multipart** 路径上 **encrypt_artifacts** 的续传检查点、失败 Abort 与指标；文档与夜间用例补充（与 **`s3-data-plane.md`** / **`artifact-encryption.md`** 互链）。 |

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
| [ ] | P2 | **CI：多版本镜像端到端矩阵（可增强）** | 在现有契约切片之上，增加 **nightly 或手动 workflow**：拉取「上一 MINOR」控制面镜像 + 当前 Agent（及反向组合），跑通最小路径（Register/Heartbeat、租约、可选 MinIO 备份片段）。验收：矩阵定义与失败告警文档化；与 **`docs/compatibility.json`** 的 `matrices` 互链。 |
| [ ] | P3 | **发版脚本与 compatibility.json 联动（可增强）** | **`scripts/bump_release.py`** 在 bump 后校验或交互式更新 **`docs/compatibility.json`** 的 **`current.control_plane_release`**；或发版文档中强制 checklist 项（与 **`verify_compatibility_matrix`** 失败信息对齐）。 |
| [ ] | P3 | **Agent 基于 server_capabilities 的降级路径（可增强）** | 当前 Agent 仅 **DEBUG** 打印 capabilities；后续可按令牌关闭 **multipart 续传**、多段 RPC 等，避免盲调未上线能力。需与 **`compute_enabled_server_capabilities`** 语义一致并加集成测试。 |

**说明**：上表三项 **[ ]**（编号 **三-11～三-13**，见 **[全量待办索引](#全量待办索引)**）为已交付能力的**后续增强**；同类条目亦见文末 **[十三、可增强项汇总](#十三可增强项汇总)**。不阻塞当前里程碑；落地后可将对应行改为 `[x]`，并同步更新**全量索引**与修订记录。

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

## 五、数据治理、加密与合规（原阶段 E）

**里程碑**：M1 · **目标**：满足常见企业安全问卷；对齐 [目标架构](../website/docs/intro/target-architecture.md) 统一存储侧的「生命周期与合规扫描」叙述。  
**原阶段**：E

| 状态 | 优先级 | 待办项 | 说明与验收要点 |
|------|--------|--------|----------------|
| [x] | P1 | **Artifact 加密（可选到默认）** | 策略 **`encrypt_artifacts`** + Agent **`DEVAULT_ARTIFACT_ENCRYPTION_KEY`**；AES-256-GCM 分块格式 **`devault-chunked-v1`**；manifest **`encryption`**；KMS/信封后续可增强。见 **`website/docs/security/artifact-encryption.md`**。 |
| [x] | P1 | **静态加密与 `encrypted` 字段真实性** | **`CompleteJob`** 读取 manifest，**`artifacts.encrypted`** 与 **`encryption`** 块一致；恢复 READ 签发 manifest 预签名供解密。 |
| [ ] | P2 | **KMS / 信封加密 / 按租户 DEK（可增强）** | 当前为 Agent 环境变量 **CMK/DEK** 直配；后续可接 **KMS 解封**、**按租户数据密钥**、manifest 记录 **密钥 ARN/版本**（非密钥材料）；选型文档与迁移路径。 |
| [ ] | P3 | **默认或租户级强制加密策略（可增强）** | 控制面或租户策略：**禁止**未加密 artifact 入库；与 **`encrypt_artifacts`**、合规问卷对齐。 |
| [x] | P1 | **保留策略与生命周期** | 策略 **`retention_days`** → **`artifacts.retain_until`**（**`CompleteJob`**）；**`devault-scheduler`** 定时删除对象 + DB 行；指标 **`devault_retention_*`**；文档 **`website/docs/guides/retention-lifecycle.md`**。存储类过渡仍在桶侧配置。 |
| [ ] | P2 | **WORM / 对象锁定（Object Lock）** | 法规保留期；需存储层与策略引擎联合设计（`development-design.md` 曾列为非目标，企业版 backlog）。 |
| [ ] | P2 | **Legal Hold** | 暂停保留期删除；审计记录。 |
| [ ] | P2 | **BYOB（客户自带 Bucket）** | [目标架构 · 统一存储与后续扩展](../website/docs/intro/target-architecture.md#unified-storage-extensions)；跨账号角色与凭证签发仍保持数据面不经 gRPC 传文件。 |

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
| [x] | P1 | **安全白皮书摘要** | **`website/docs/security/security-whitepaper.md`**：信任边界、密钥流、审计、gRPC 指标告警引用、明确未实现项（KMS/BYOB/WORM 等）。 |
| [x] | P2 | **`docs/README.md` 与实现差距表** | 仓库 **`docs/README.md`**：对照 **`docs-old/README.md`** 愿景条目的实现状态表与站内链接。 |

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
| E-DB-001 | 数据库备份 MVP | M2 | C |

**Epic → 排期波次**（与 **[排期波次与全量待办索引](#排期波次与全量待办索引)** 一致）：**E-OPS-001** 中 **Helm / K8s** 与 **告警路由（Prometheus + Alertmanager）** 已交付；**`E-DATA-001` / `E-DATA-002`** 之 **§二 Multipart×加密**、**E-VER-001** 之 **§三 CI / bump_release / capabilities** → **波次 2**；**E-ARCH-001** 之 **§一** 两项可增强 → **波次 3**；**E-GOV-001** 之 **KMS、强制加密、WORM、Legal Hold、BYOB** → **波次 4**；**E-DB-001** → **波次 5**；**E-TRUST-001** 之 **§七 增量与时间线** → **波次 6**。其余 Epic 主线条目在当前仓库已为 `[x]`。

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
| 2026-05-09 | **清单重组**：新增 **排期波次（1～6）**、**全量待办索引**（§零～§九 + §三.3 注，共 73 行，与分节表一一对应）；**整体实施路线** 补充排期原则；**如何使用** 增加「排期波次」列说明；**§十** 增加 Epic→波次映射；**§十三** 与全量索引互链。 |
| 2026-05-09 | **M1·六 P2**：**Helm Chart** 落地（`deploy/helm/devault`、CI `helm lint`、文档 **`website/docs/install/kubernetes-helm.md`**）；**§六** 与全量索引 **六-05** 勾选；**波次 1** 表更新。 |
| 2026-05-09 | **M1·六 P2**：**告警路由** 落地（`deploy/alertmanager.yml`、`deploy/docker-compose.prometheus.yml` 扩展、**`deploy/prometheus/alerts.yml`** 增补策略锁/保留清理；Helm **`templates/monitoring.yaml`** + **`prometheus-alerts.yml`**；**`website/docs/install/observability.md`** 重写 Alertmanager 章节；**§六** 与全量索引 **六-06** 勾选；**波次 1** 标为已收敛）。 |

---

## 十三、可增强项汇总

**非阻塞、可后续排期。** 以下与上文 **`（可增强）`** 或 **已勾选行内「后续」表述**对应，便于**单独 Epic / 季度排期**；实现后可在**归属章节**、**[全量待办索引](#全量待办索引)** 与下表同步勾选。

**说明**：**§六** Helm/告警、**§五** WORM/Legal Hold/BYOB、**§七** 增量时间线、**§九** 数据库 MVP 等未勾选项**未列入**下表（多为非「可增强」标签之主线扩展）；其 **排期波次** 仍以 **[排期波次与全量待办索引](#排期波次与全量待办索引)** 为准。

| 状态 | 优先级 | 归属 | 待办项 | 说明与验收要点 |
|------|--------|------|--------|----------------|
| [ ] | P3 | §一 | **Envoy local_rate_limit** | 见 **§一** 表；网关侧补充限流 filter 与文档。 |
| [ ] | P3 | §一 | **Register → 每 Agent 令牌 / 吊销 / Redis** | 见 **§一** 表；与 gRPC 审计、`reason_code` 一致。 |
| [ ] | P3 | §二 | **Multipart × 加密联调** | 见 **§二** 表；大对象 + **`encrypt_artifacts`** 边界与文档。 |
| [ ] | P2 | §三.2 | **CI 多版本镜像 E2E 矩阵** | nightly/手动 workflow；与 **`docs/compatibility.json`** `matrices` 互链。 |
| [ ] | P3 | §三.2 | **bump_release ↔ compatibility.json** | 发版脚本校验或交互更新 **`current.control_plane_release`**。 |
| [ ] | P3 | §三.2 | **Agent 按 server_capabilities 降级** | 关闭 multipart 续传等盲调路径；集成测试与 **`compute_enabled_server_capabilities`** 对齐。 |
| [ ] | P2 | §五 | **KMS / 信封 / 租户 DEK** | 见 **§五** 表。 |
| [ ] | P3 | §五 | **默认或租户级强制加密** | 见 **§五** 表。 |
