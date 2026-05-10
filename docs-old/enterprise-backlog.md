# DeVault 企业级落地待办清单

> **文档目的**：在 [`development-design.md`](./development-design.md) 与 [**目标架构（文档站）**](../website/docs/intro/target-architecture.md) 之上，结合当前代码实现，列出使项目**可长期作为企业级备份方案**交付所需的完整待办项，便于排期、分工与验收。  
> **基线说明（截至文档编写时的实现）**：S1/S2 文件备份主路径已落地；执行单元为**边缘 Agent（Pull + gRPC 租约）**，Celery Worker 已移除；控制面为 FastAPI + 内嵌 gRPC + APScheduler + PostgreSQL + Redis；对象存储以 **S3 兼容 + 预签名 URL** 为主路径；`development-design.md` 第 20 节中 **S3 数据库 MVP 仍为未完成**。  
> **索引**：**§零～§九**、**§十四**、**§十五**（追加）的**活跃**未完成项见 **[排期波次与全量待办索引](#排期波次与全量待办索引)**（位于 **§零** 之后）；**`[x]` 历史索引行**见 **[`enterprise-backlog-completed-archive.md`](./enterprise-backlog-completed-archive.md)**。维护时请与 **§分节表** 同步勾选。

---

## 如何使用本文档

| 列 | 含义 |
|----|------|
| **里程碑** | **M1** = 平台与企业级能力（建议优先）；**M2** = 在 M1 达标后接入的**新备份类型**（数据库 MVP 等）。 |
| **优先级** | P0：安全与架构底线；P1：可靠性/规模；P2：功能扩展；P3：合规与运营增强。 |
| **依赖** | 实施前建议满足的前置项（见各节末）。 |
| **原阶段字母** | 历史编号（A～I），见文末「重组对照表」，便于与旧讨论、Epic 对齐。 |
| **可增强** | 已交付主线之上的**后续增强**；历史汇总表见 **[归档 Part 2 · §十三](./enterprise-backlog-completed-archive.md#十三可增强项汇总归档表内均已-x)**；**不阻塞**当前里程碑。 |
| **排期波次** | 跨章节的建议实施顺序（**1**～**7**），与 **P0～P3** 独立；定义见 **[排期波次与全量待办索引](#排期波次与全量待办索引)**。 |
| **Web UI 同步** | **§十四 · 十四-16～十四-18**：后端迭代须与 **`/ui/*`** 同期或登记豁免；详见上文 **「整体实施路线」** 与 **§十四 · 14.3**。**§十五**：企业交付用 **Ant Design Pro** SPA（Bearer + `X-DeVault-Tenant-Id`）与 REST 对等；**下线 Jinja `/ui`** 后 **十四-17** 类闸门迁移至 `console/` / OpenAPI；**十四-18** 仍约束 M2 与 UI 同期。 |

完成某项后，可将 `[ ]` 改为 `[x]`，并在 **归属分节表**（含 **§十四**、**§十五**）、**全量待办索引（活跃）**（必要时将 **`[x]` 行摘要** 追加至 **[归档](./enterprise-backlog-completed-archive.md)** 的「闭合记录」）与 PR / **§十二、修订记录** 中注明。

---

## 整体实施路线（先平台、后数据库）

**策略**：优先完成 **M1 企业级平台能力**（传输与身份、数据面可靠性、版本与兼容、租户与治理、运维与信任、对外文档），再在稳定平台上接入 **M2 数据库备份** 等新产品能力。  
**原因简述**：数据库 dump 体积大、耗时长，会放大弱网、断点续传、租约与升级兼容等问题；平台能力与其正交，先夯实可减少返工。  
**维护原则**：**活跃待办**以本文件 **§七 / §九 / §十四 / §十五** 与 **「全量待办索引（活跃）」** 为准；**已闭合**分节正文、**§十三**、历史 **§十二** 修订与 Epic 长说明均在 **[归档 Part 2](./enterprise-backlog-completed-archive.md#分节正文与历史归档part-2)**，主文件**不重复**粘贴。  
**索引表维护（2026-05-10 起）**：**`[x]`** 索引行在 **[`enterprise-backlog-completed-archive.md`](./enterprise-backlog-completed-archive.md)** **Part 1** 同步追加；本表保留 **§十五** 全量 **`[x]`** 行便于对照 **§15.2**；**未完成**仅为 **`[ ]`** 与 **`三-注`**。  
**排期原则（2026-05-09 起）**：在 **M1 波次 1～2**（基础设施闭环 + 发布/数据面韧性）未收敛前，**默认不启动 M2（§九）**；§七「增量与时间线」绑定 M2，随 **波次 6** 处理。  
**Web UI 同步原则（2026-05-10 起）**：控制面 **REST/OpenAPI** 与 **Web UI（`E-UX-001`）** 按 **竖切同期验收**——**§十四** 每条后端能力默认 **同一发布周期** 交付 **`/ui/*` 最小可用面**（列表 / 表单 / 详情至少其一）；若仅 API 先合并，须在 PR 或 **`website/docs/guides/web-console.md`** 登记 **豁免与回填截止**，并由 **十四-16** 作为流程待办持续监督直至闭合。**M2（§九）** 数据库能力须执行 **十四-18**（**波次 5**），避免「仅 curl 可用却宣称 GA」。**十四-17** 为字段一致性与 RBAC 闸门（可与 CI/PR 模板挂钩）。**§十五** 落地后，人机主入口以 **Ant Design Pro 控制台** 为交付形态（**Bearer**；**不沿用** Jinja 平铺导航）；**八-04～八-09** 仍为已交付的 **HTML 最小 UI** 历史记录，由 **十五-19** 负责下线代码与迁移闸门。

---

> **已闭合正文**：§零～§八、§五～§八 分节表、完整 **§十四**、**§十三**、**§十二** 历史修订与 **§十** 长说明 → **[`enterprise-backlog-completed-archive.md` · Part 2](./enterprise-backlog-completed-archive.md#分节正文与历史归档part-2)**。

## 排期波次与全量待办索引

### 排期波次（建议实施顺序）

下列 **波次** 为结合当前代码实现后的**跨章节排期**（先收口 M1 基础设施与可运维性，再强化发布/数据面韧性，然后网关身份与合规扩展，最后启动 M2）。**不改变**各分节表中 **P0～P3** 的语义（安全/架构底线仍以 P0 为准）。

| 波次 | 名称 | 未完成条目（§ 指向） |
|------|------|------------------------|
| **1** | M1 基础设施与运维闭环 | **已收敛**：Helm（`deploy/helm/devault`）+ **告警路由**（`deploy/alertmanager.yml`、`deploy/docker-compose.prometheus.yml`、`monitoring.enabled`、文档 **`website/docs/install/observability.md`**） |
| **2** | 发布工程与数据面韧性 | **已收敛**：§二 Multipart×加密；§三 CI 多版本镜像 E2E；§三 **`bump_release` ↔ `compatibility.json`**；§三 Agent **`server_capabilities`** 降级 |
| **3** | 网关与身份演进 | **已收敛**：§一 Envoy **`local_rate_limit`**；§一 Register **每 Agent Redis 会话** + **`POST …/revoke-grpc-sessions`** |
| **4** | 合规与统一存储 \| **控制台与 API 对等** | **§五**：已从迁移 **`0010`** 等落地（详见 **§五**、**§十**）；**§八**：**八-04～八-09**（Jinja `/ui`）已落地；**企业交付控制台**见 **§十五**（Ant Design Pro，`console/`，与 REST 对等；**十五-19** 下线旧 `/ui` 与 CI 模板闸门迁移）。 |
| **5** | M2 数据库备份 MVP | §九 全部未完成项 + **§十四 · 十四-18**（Web UI 与 §九 API **同期**；建议在 **波次 1～2** 收敛后再启动） |
| **6** | 长期（依赖 M2） | §七 增量与时间线 |
| **7** | M1 Agent 租户隔离与执行路由（Greenfield） | **§十四** **十四-15** 待收口（**十四-01～十四-14**、**十四-16～十七** 已收口）；与 **波次 3～4** 可部分并行；**不考虑向后兼容**，见 **§十四** 首段说明 |
| **—** | 已完成 | 索引 **`[x]`** 与 **§零** 基线等闭合内容见 **[归档](./enterprise-backlog-completed-archive.md)**（含 **Part 2**） |

### 全量待办索引（活跃）

**`[x]` 历史索引行**在 **[`enterprise-backlog-completed-archive.md`](./enterprise-backlog-completed-archive.md)** **Part 1** 同步维护；本表 **§十五** 仍列出全部 **`[x]`** 行以便与 **§15.2** 对照。未完成项为 **`[ ]`** 与 **`三-注`**（下表：**十四-15**、**十四-18**、**七-03**、**§九** 等）。**已闭合分节表全文**在 **[Part 2](./enterprise-backlog-completed-archive.md#分节正文与历史归档part-2)**。

| 编号 | 章节 | 状态 | P | 排期 | 待办项（摘要与分节表标题一致） |
|------|------|------|---|------|------------------------------|
| 三-注 | §三.3 | — | — | — | **CHANGELOG 编写约定**（持续流程；正文见 **[归档 Part 2](./enterprise-backlog-completed-archive.md#分节正文与历史归档part-2)** 内 **§三 · 3.3**） |
| 十四-15 | §十四 | [ ] | P3 | 7 | **文档与 Quickstart：多租户拓扑、密钥生命周期、池 vs 单 Agent、与 NetBackup 类心智对照** |
| 十四-18 | §十四 | [ ] | P1 | 5 | **M2：§九 数据库 MVP 的 Web UI 与 API 同期排期（波次 5 内闭合）** |
| 十五-01 | §十五 | [x] | P0 | 4 | **`GET /api/v1/auth/session`（或等价）**：返回 `role`、`principal_label`、`allowed_tenant_ids`，供控制台 `getInitialState` 与菜单权限 |
| 十五-02 | §十五 | [x] | P0 | 4 | **OpenAPI → TypeScript** 与 **`console/`** CI **`typecheck`**（契约单一事实源） |
| 十五-03 | §十五 | [x] | P0 | 4 | **Ant Design Pro（Umi 4）** 工程 **`console/`** 初始化与品牌/主题基线 |
| 十五-04 | §十五 | [x] | P0 | 4 | **`request` 拦截器**：`Authorization: Bearer`、`X-DeVault-Tenant-Id`；401/403 统一处理 |
| 十五-05 | §十五 | [x] | P0 | 4 | **`getInitialState` + `access.ts`**（`canAdmin` / `canWrite` 与 §四 RBAC 对齐） |
| 十五-06 | §十五 | [x] | P0 | 4 | **登录页（Bearer/token）**与存储策略（不用 HTTP Basic 弹窗） |
| 十五-07 | §十五 | [x] | P0 | 4 | **顶栏租户选择器**（`GET /tenants` + `allowed_tenant_ids`；替代 Cookie **`POST /ui/context/tenant`**） |
| 十五-08 | §十五 | [x] | P0 | 4 | **开发 `proxy` 与生产同域 `/api` 反代**（文档 + Compose/Helm 可选） |
| 十五-09 | §十五 | [x] | P1 | 4 | **ProLayout**：侧栏五大分组（概览 / 备份与恢复 / 执行面 / 合规与演练 / 平台管理）+ 顶栏环境标识与 **help**（`/docs`、`/metrics`、`/version`、`/healthz` 新窗） |
| 十五-10 | §十五 | [x] | P1 | 4 | **工作台 MVP**（最近失败 Job、`/version`；聚合可增强） |
| 十五-11 | §十五 | [x] | P1 | 4 | **作业中心**：`ProTable`、筛选、取消/重试、**详情抽屉**（`config_snapshot`、`result_meta`、hostname 审计字段） |
| 十五-12 | §十五 | [x] | P1 | 4 | **策略 CRUD + Tab 表单**（路径/KMS/Object Lock/retention）+ **策略—计划关联 UX**（按 `policy_id` 聚合 Schedules） |
| 十五-13 | §十五 | [x] | P1 | 4 | **发起备份**（`policy_id` 或内联 `config`）+ **`POST /jobs/path-precheck`** |
| 十五-14 | §十五 | [x] | P1 | 4 | **制品列表/详情、分页**；**恢复 / 恢复演练**（`POST /jobs/restore`、`restore-drill`） |
| 十五-15 | §十五 | [x] | P1 | 4 | **`Schedules` 与 `restore-drill-schedules` 全 CRUD** |
| 十五-16 | §十五 | [x] | P2 | 4 | **租户内 Agents** + **Agent pools** 全流程（与策略执行绑定互链） |
| 十五-17 | §十五 | [x] | P2 | 4 | **全舰队 Agents**、单 Agent **详情**、**Enrollment** `GET/PUT`、**吊销 gRPC**（管理员分区 + 强确认） |
| 十五-18 | §十五 | [x] | P2 | 4 | **Legal hold UI**（admin）+ **Tenants** 管理员表单（`TenantPatch` 全字段：BYOB、KMS、`policy_paths_allowlist_mode` 等） |
| 十五-19 | §十五 | [x] | P3 | 4 | **下线 Jinja `/ui`**（删 `routes/ui.py`、`web/templates/`、仅 UI 的 Basic/Cookie 依赖）；**替换 `verify_ui_openapi_registry.py`** 为 `console`/OpenAPI 闸门 |
| 十五-20 | §十五 | [x] | P3 | 4 | **文档站**：`web-console.md`、`README` 等改为 **Ant Design Pro + Bearer**；与 **十四-18** 叙述对齐 |
| 十五-21 | §十五 | [x] | P3 | 4 | **交付镜像**：`console` 静态（nginx）+ **Compose / Helm Ingress** |
| 十五-22 | §十五 | [x] | P3 | 4 | **Playwright E2E** 冒烟（登录 → 作业中心 → 可选切租户 → 备份向导；**`deploy/docker-compose.console-e2e.yml`**） |
| 十五-23 | §十五 | [x] | P3 | 4 | **（可增强）** 列表 API **query**：**`GET /jobs?kind=&status=`** |
| 十五-24 | §十五 | [x] | P3 | 4 | **（可增强）** 备份链路**向导**、工作台 **Grafana`/metrics`** 入口 |
| 七-03 | §七 | [ ] | P2 | 6 | **增量与时间线（长期）** |
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

## 十四、多 Agent / 多租户执行隔离与策略路由（Greenfield）

**文档位置**：为追加章节，物理上列于 **§四（租户）** 之后、**§五** 之前；**里程碑归属仍为 M1**（企业级平台能力扩展）。  
**里程碑**：M1 · **目标**：在共享控制面、多 Agent、多租户与强运维管控前提下，建立 **Agent 身份 ↔ 授权租户** 的硬边界、**策略 ↔ 执行面（Agent 或池）** 的可选绑定，以及 **路径与主机可解释、可审计** 的用户体验；降低「路径写在哪台机、谁领了作业」的心智成本。  
**排期波次**：建议 **波次 7**（见 **[排期波次与全量待办索引](#排期波次与全量待办索引)**）；可与 **波次 3～4**（网关身份、控制台）部分并行，但 **P0 隔离项** 应在对外承诺多租户 SaaS 前收口。  
**范围说明（与历史待办关系）**：本节为 **2026-05-10** 起 **追加**；**已闭合 `[x]` 分节行**见 **[归档 Part 2 · §十四](./enterprise-backlog-completed-archive.md#十四完整分节归档快照)**。实现本节时 **不要求向后兼容**（无旧 Agent/旧策略并存约束；迁移策略由实施 PR 自定）。

### 14.1 优先级分层（实施顺序建议）

| 层级 | 主题 | 索引编号 |
|------|------|-----------|
| **P0** | 安全与隔离：注册与凭据绑定租户、`LeaseJobs` 及作业链 tenant 硬过滤、存储与元数据隔离复核、吊销与轮换 | **十四-01～十四-04**（**已收口**） |
| **P1** | 路由与策略模型：策略绑定 `agent_id` 或 `agent_pool_id`、池抽象、调度/租约/failover 语义 | **十四-05～十四-07**（**已收口**） |
| **P2** | 可观测与体验：Heartbeat 主机与 allowlist、租户范围 Agent 列表、策略表单联动校验、预检 Job、作业展示 lease + hostname 快照 | **十四-08～十四-12**（**已收口**） |
| **P3** | 运营与文档：告警与 SLO、批量/IaC、拓扑与 Quickstart | **十四-13～十四-14** 已收口；**十四-15** 待办 |
| **P1** | **Web UI 与 API 同期交付**：流程监督 + **M2** 数据库界面与 **§九** 锁波次 | **十四-16、十四-18** |
| **P2** | **Web UI 工程闸门**：OpenAPI/模板/RBAC/CHANGELOG 一致性（Jinja 阶段 **十四-17**；SPA 阶段迁移见 **§十五 · 十五-19**） | **十四-17** |
| **P0～P3** | **企业控制台（Ant Design Pro）**：Bearer、布局重构、全量 REST 能力、下线 **`/ui`** | **§十五 · 十五-01～十五-24**（**已全部收口**；活跃索引无 `[ ]` 十五项） |

### 14.2 分节待办表（仅 **`[ ]`**；已闭合 **`[x]`** 行见 [归档 Part 2](./enterprise-backlog-completed-archive.md#分节正文与历史归档part-2)）

| 状态 | 优先级 | 待办项 | 说明与验收要点 |
|------|--------|--------|----------------|
| [ ] | P3 | **文档与 Quickstart** | 多租户拓扑图、密钥生命周期、池 vs 单 Agent、与「客户端 + 策略」类备份产品心智对照；更新 **`website/docs/user/quickstart.md`** 等入口。 |
| [ ] | P1 | **M2：§九 数据库 MVP 的 Web UI 与 API 同期排期（波次 5 内闭合）** | **九-01～九-04** 每条须有 **向导 / 列表 / 详情 / 双重确认** 中与能力对等的最小 UI；排期绑定 **波次 5**，与 **§八** 已落地模式一致；**验收**：不在「仅 REST/CLI 可用」状态下对外宣称数据库备份 **GA**。 |

**依赖**：**§一** Register/会话模型；**§四** 租户与 RBAC；**§六** 观测与 Agent 舰队；**§八** 控制台策略表单（Jinja 历史）；**`E-UX-001`**（**§八** + **§十五**）与 **十四-16～十八** 为 **交付节奏** 交叉依赖。可与 **§九** 数据库 MVP 并行设计 proto，但 **P0 建议先于对外多租户承诺** 交付。

### 14.3 Web UI 与 REST 同步排期（摘要）

| 索引 | 排期波次 | 要点 |
|------|----------|------|
| **十四-16** | **7**（主）、持续 | **竖切**：后端能力与 **`/ui/*`** 同期或豁免登记；**`guides/web-console.md`** 为缺口台账之一。 |
| **十四-17** | **7**（主） | **闸门**：字段、角色、变更可见性与 **OpenAPI** 对齐。 |
| **十四-18** | **5** | **M2**：**§九** 能力与控制台 **同波次闭合**，见上表 **十四-18** 行。 |
| **十五-01～十五-24** | **4**（主）、**3**（收尾） | **Ant Design Pro 企业控制台**：见 **§十五** 与归档 **Part 1** 增补行；**十五-19** 下线 Jinja **`/ui`** 后 **十四-17** 闸门迁移至 `console/`。 |

---

## 十五、企业控制台（Ant Design Pro · 前后端分离）

**文档位置**：紧接 **§十四** 之后、**§五** 之前（与上文 **「全量待办索引（活跃）」** 表中 **十五-xx** 位于 **十四-18** 与 **七-03** 之间一致）。**里程碑**：M1 · **目标**：以 **Umi 4 + Ant Design Pro** 交付**可给客户的人机控制台**；**仅调用** 现有 **`/api/v1/*` REST**（Bearer + **`X-DeVault-Tenant-Id`**）；**信息架构**按「概览 / 备份与恢复 / 执行面 / 合规与演练 / 平台管理」分组，**不沿用** Jinja **`base.html`** 平铺导航。**范围说明**：实现 **不要求** 与旧 **`/ui/*`** HTTP Basic、Cookie 租户切换向后兼容（见 **十五-19**）；**八-04～八-09** 为已交付 HTML 能力的历史记录，闭合 **§十五** 后代码路径以下线为准。

### 15.1 优先级分层（与索引 **十五-01～十五-24** 对应）

| 层级 | 主题 | 索引编号 |
|------|------|-----------|
| **P0** | 契约与基座：`auth/session`、OpenAPI→TS、脚手架、`request`/`access`、登录、租户头、代理与部署约定 | **十五-01～十五-08** |
| **P1** | 租户主路径：布局壳、工作台、作业中心、策略/制品/计划/演练队列、路径预检与内联备份 | **十五-09～十五-15** |
| **P2** | 执行面与平台管理：租户内 Agent、池、全舰队、Enrollment、吊销、Legal hold、Tenants 全字段 | **十五-16～十五-18** |
| **P3** | 下线旧 UI、文档、镜像与 E2E；可增强项 | **十五-19～十五-24**（**已收口**） |

### 15.2 分节待办表（与活跃索引一一对应）

| 状态 | 优先级 | 待办项 | 说明与验收要点 |
|------|--------|--------|----------------|
| [x] | P0 | **`GET /api/v1/auth/session`（或等价）** | JSON：`role`、`principal_label`、`allowed_tenant_ids`（与 `AuthContext` 一致）；未认证 401；供 **`getInitialState`**、**`access.ts`**、租户下拉过滤。 |
| [x] | P0 | **OpenAPI → TS + CI** | **`openapi-typescript`**（或等价）消费 **`/openapi.json`**；**`console/`** 在 CI 中 **`tsc --noEmit`**（或项目等价命令）。 |
| [x] | P0 | **Ant Design Pro（Umi 4）脚手架** | 目录 **`console/`**（与 `website/` 文档站分离）；`title`、默认语言、主题占位。 |
| [x] | P0 | **`request` 全局头** | **`Authorization: Bearer`**、**`X-DeVault-Tenant-Id`**；**401** 清态跳转登录；**403** 统一 **`message`**。 |
| [x] | P0 | **`getInitialState` + `access`** | **`canAdmin`** / **`canWrite`**；**auditor** 仅只读路由与按钮。 |
| [x] | P0 | **登录页** | 录入 **API token / OIDC 解析链可接受的 raw token**（与 REST 一致）；**不**使用浏览器 HTTP Basic 弹窗。 |
| [x] | P0 | **顶栏租户选择器** | **`GET /api/v1/tenants`** + 主体 **`allowed_tenant_ids`** 过滤；持久化所选 UUID；**删除** **`devault_ui_tenant`** Cookie 与 **`POST /ui/context/tenant`**。 |
| [x] | P0 | **联调与生产路径** | **`config/proxy`** 指向本地 API；文档约定 **`/`** 静态 + **`/api`** 反代；可选 Compose 服务 **`console`**。 |
| [x] | P1 | **ProLayout 与顶栏** | 侧栏 **五大分组**；顶栏 **环境标签**、**帮助下拉**（`/docs`、`/metrics`、`/version`、`/healthz` 新窗口）。 |
| [x] | P1 | **工作台 MVP** | 最近失败/进行中 **Jobs**；可选 **`GET /version`** 卡片。 |
| [x] | P1 | **作业中心** | **`ProTable`** + **`GET/POST /api/v1/jobs/*`**；详情抽屉展示 **`config_snapshot`**、**`result_meta`**、**`lease_agent_hostname`** / **`completed_agent_hostname`**。 |
| [x] | P1 | **策略 + 关联计划** | **`/policies` CRUD**；表单 **Tab** 对齐 **`FileBackupConfigV1`**；策略详情内嵌 **Schedules**（列表客户端按 **`policy_id`** 过滤）。 |
| [x] | P1 | **备份与预检** | **`POST /jobs/backup`**（**`policy_id` 或内联 `config`**）；**`POST /jobs/path-precheck`**。 |
| [x] | P1 | **制品与恢复** | **`GET /artifacts`** 分页列表 + **`GET /artifacts/{id}`** 详情；**`POST /jobs/restore`**、**`POST /jobs/restore-drill`**；危险操作二次确认。 |
| [x] | P1 | **Cron 资源** | **`/schedules`**、**`/restore-drill-schedules`** 全 CRUD。 |
| [x] | P2 | **租户内 Agent 与池** | **`GET /tenant-agents`**；**`agent-pools`** 列表/详情/members；与策略 **`bound_*`** 互链。 |
| [x] | P2 | **全舰队与登记** | **`GET /agents`**、**`GET /agents/{id}`**；**`GET/PUT .../enrollment`**；**`POST .../revoke-grpc-sessions`**（仅 **admin**、强确认）。 |
| [x] | P2 | **Legal hold + Tenants** | **`PATCH .../legal-hold`**；**`PATCH /tenants/{id}`** 覆盖 **BYOB / KMS / `policy_paths_allowlist_mode` / `require_encrypted_artifacts`** 等。 |
| [x] | P3 | **下线 Jinja UI** | 移除 **`ui` router**、**`web/templates/**`**、**`verify_ui_basic_auth`**、**`get_effective_tenant_ui`** 等；**CI** 以 **`verify_console_openapi_contract.py`** + **`console/`** **`npm run build`** 替代 **`verify_ui_openapi_registry.py`**。 |
| [x] | P3 | **文档** | **`website/docs/guides/web-console.md`**、**`website/docs/user/web-console.md`**、**`CONTRIBUTING.md`** 等：入口为 **`console/`** SPA；**十四-18** 中「Web UI」指本控制台与后续 M2 页。 |
| [x] | P3 | **镜像与 Ingress** | **`deploy/Dockerfile.console`**（多阶段 **`dist`**+nginx）；Compose **`console`** **`build`**；Helm **`console.enabled`** + Ingress **`/api`** 等与 **`/`** 拆分。 |
| [x] | P3 | **Playwright E2E** | **`console/e2e/`** + **`playwright.config.ts`**；**`.github/workflows/console-e2e.yml`** 驱动 **`deploy/docker-compose.console-e2e.yml`**（源码构建 API+console）；登录 → **作业中心** → 顶栏可选**第二租户** → **`/backup/run`** 向导步骤可见。 |
| [x] | P3 | **（可增强）列表 query** | **`GET /api/v1/jobs?kind=&status=`**（**`JobKind` / `JobStatus`** 校验）；作业中心 **`ProTable`** 传参服务端过滤；契约见 **`scripts/verify_console_openapi_contract.py`** + **`tests/test_openapi_jobs_list_filters.py`**。 |
| [x] | P3 | **（可增强）向导与聚合** | **发起备份**三步 **Steps**（方式 → 参数 → 确认）；工作台 **指标与看板**卡片：**`/metrics`** 外链 + 可选 **`UMI_APP_GRAFANA_URL`**（**`console/.env.example`**）。 |

**依赖**：**§四** RBAC 与租户头语义；**§十四** 执行绑定与 Agent 模型；**`E-UX-001`**（**§八** 历史 HTML 已交付，本 § 为其企业形态演进）。与 **十四-18**（M2 UI 同期）交叉时，控制台须预留 **数据库 Job/Policy** 路由占位或特性开关。

---

## 七、备份验证与持续信任（仅存未完成；已闭合行见 [归档 Part 2](./enterprise-backlog-completed-archive.md#分节正文与历史归档part-2)）

**里程碑**：M1 · **原阶段**：G

| 状态 | 优先级 | 待办项 | 说明与验收要点 |
|------|--------|--------|----------------|
| [ ] | P2 | **增量与时间线（长期）** | WAL/binlog、PITR（`development-design.md` §3.4 非目标）；单独 Epic，依赖数据库插件成熟。 |

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
| E-UX-001 | Web 控制台与 REST 对等 | M1 | H（扩充）+ **§十四 · 十四-16～十七**（同步排期闸门）+ **十四-18**（M2 与 §九 同期）+ **§十五**（Ant Design Pro 企业控制台；**十五-19** 下线 Jinja **`/ui`**） |
| E-DB-001 | 数据库备份 MVP | M2 | C |
| E-MT-002 | 多 Agent 租户隔离与策略执行路由（Greenfield） | M1 | §十四（与 D/F/H 交叉） |

**Epic→波次** 长说明已迁至 **[归档 Part 2](./enterprise-backlog-completed-archive.md#分节正文与历史归档part-2)**（节内 **「十、Epic 映射表 + 波次长说明」**）。

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
| （追加） | M1 · **十五、企业控制台（Ant Design Pro）**（**正文**紧接 **§十四**、在 **§五** 之前；活跃索引 **十五-01～十五-24** 紧接 **十四-18** 之后） |

**说明**：上表 **A～H** 与 **§零～§八** 分节正文已迁至 **[归档 Part 2](./enterprise-backlog-completed-archive.md#分节正文与历史归档part-2)**，本表仅保留章节映射。

---

## 十二、修订记录

| 日期 | 变更 |
|------|------|
| 2026-05-10 | **索引 + 活跃表**：全量索引 **`[x]`** 行迁至本仓库 **`enterprise-backlog-completed-archive.md`**；主表仅 **`[ ]`**、**`三-注`** 与 **十五-01～二十四**；**§十五** 入册。 |
| 2026-05-10 | **十五-01～02 闭合**：**`GET /api/v1/auth/session`**；**`console/`** OpenAPI→TS + CI **`typecheck`**（**`scripts/export_openapi_json.py`**）。 |
| 2026-05-10 | **十五-03～06 闭合**：**`@umijs/max` + Pro 脚手架**；**`request` 拦截器**；**`getInitialState` / `access.ts`**；**`/user/login`** Bearer + **`localStorage`**；CI **`npm run build`**。 |
| 2026-05-10 | **十五-07～10 闭合**：租户顶栏、**`proxy`/`nginx`/Compose `console`**、五大分组菜单、工作台 **`/version`+Jobs**。 |
| 2026-05-10 | **正文与历史全量归档**：§零～§八、§五～§八、完整 §十四、§十三、§十二 历史修订与 Epic 长说明 → **[归档 · Part 2](./enterprise-backlog-completed-archive.md#分节正文与历史归档part-2)**；本文件瘦身。 |
| 2026-05-10 | **十五-11～十八 闭合**：`console/` 嵌套路由交付作业中心、策略（Tab + 内嵌计划）、发起备份/路径预检、制品（恢复/演练/Legal hold）、两套 Cron CRUD、租户 Agent/池/舰队与登记吊销、平台租户 **`TenantPatch`**；**`CHANGELOG`**、**`console/README.md`**、**`website/docs/guides/web-console.md`**、**`website/docs/user/web-console.md`** 同步。 |
| 2026-05-10 | **十五-19～二十一 闭合**：下线 Jinja **`/ui`**（**`routes/ui.py`**、**`web/templates/`**、**`deps.py`** UI Basic/Cookie）；策略路径合并逻辑迁至 **`services/policy_paths_form_merge.py`**；**`scripts/verify_console_openapi_contract.py`** + CI；**`deploy/Dockerfile.console`** 与 Compose **`console`** **`build`**；Helm **`console`** Deployment/Service/ConfigMap + Ingress 拆分；文档与 **§十五 · 15.2** 同步。 |
| 2026-05-10 | **十五-22～二十四 闭合**：**Playwright** 冒烟（**`console/e2e/`**、**`deploy/docker-compose.console-e2e.yml`**、**`.github/workflows/console-e2e.yml`**）；**`GET /api/v1/jobs`** 增加 **`kind`/`status`** 查询；控制台作业列表与 OpenAPI 闸门同步；**发起备份**向导 **Steps**；工作台 **Grafana`/metrics`** 入口与 **`UMI_APP_GRAFANA_URL`**；活跃索引与归档 **Part 1**、**`CHANGELOG`**、**`guides/user/web-console`** 同步。 |

