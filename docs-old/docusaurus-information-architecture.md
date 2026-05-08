# DeVault 文档站（Docusaurus）信息架构 — 参考稿

> **用途**：本文件为「从零设计」的 Docusaurus 站点结构与层级说明，供后续在仓库中搭建文档系统时对照实现。  
> **范围**：不绑定 `docs-old` 内既有 Markdown 的文件名或 URL；正式文档将写在新的 `website/docs/`（或等价路径）中，**不要求与旧文档向后兼容**。

---

## 1. 设计原则

1. **按读者任务组织**，不按历史设计文档的文件名组织。
2. **URL 稳定、语义清晰**：目录与文件建议使用 **英文 slug**（例如 `/docs/install/docker-compose`），正文标题可用中文；利于外链与 SEO。
3. **每层单一职责**：概念与操作分离；网络与安全、存储、API 参考各自成章，避免单页过长。
4. **根 README 分工**：仓库根 `README.md` 保留极简说明 + **一条**完整文档站入口；细节全部进 Docusaurus，避免双处长期分叉。

---

## 2. 推荐仓库布局

采用 Docusaurus 官方惯例：

- 在仓库根下新建 **`website/`**（名称可改，但需与 CI 一致）。
- 正式文档根目录：**`website/docs/`**，内文全部为**新写**的 Markdown/MDX，不引用本目录（`docs-old`）作为线上源。

```
website/
  docs/                 # 按下文 IA 建子目录与 .md
  src/pages/            # 站点首页 index.md(x)、可选独立页面
  docusaurus.config.ts
  sidebars.ts
  package.json
```

可选：根目录 `Makefile` / Task 中增加 `docs` 目标，内部执行 `cd website && npm run start` 等。

---

## 3. 侧栏顶层分组与建议文件

以下为建议的 **文件路径（相对于 `website/docs/`）** 与 **内容要点**。实现时通过 `sidebars.ts` **手写分组**与顺序；每篇建议使用 front matter：`title`、`description`、`sidebar_position`。

### 3.1 入门 `intro/`

| 建议路径 | 内容要点 |
|----------|----------|
| `intro/index.md` | 产品定位、适用场景、与近似方案的差异、**术语表**（控制面、Agent、任务、策略、租约等） |
| `intro/quickstart.md` | 最短路径跑通：Compose 起服务 → 一次备份 → 校验恢复；仅描述当前真实行为 |
| `intro/architecture-overview.md` | 控制面 + Agent + 对象存储的逻辑关系概览（图或文字均可） |

**侧栏顺序建议**：入门 → `index` → `quickstart` → `architecture-overview`

---

### 3.2 安装与运行 `install/`

| 建议路径 | 内容要点 |
|----------|----------|
| `install/requirements.md` | 运行时版本、依赖服务（Postgres、Redis、S3 等） |
| `install/docker-compose.md` | 本地/演示 Compose；各服务角色（api、scheduler、agent、minio-init 等） |
| `install/database-migrations.md` | Alembic、首次升级、多实例下由谁执行迁移 |
| `install/configuration.md` | 环境变量分组说明（表格）；与 `deploy/` 中示例一致 |
| `install/observability.md` | Prometheus、`/metrics`、健康检查、日志要点 |

**侧栏分组名建议**：安装与运行

---

### 3.3 网络与安全 `security/`

| 建议路径 | 内容要点 |
|----------|----------|
| `security/agent-connectivity.md` | Agent 与控制面的连接方式、gRPC 端口、生产拓扑 |
| `security/tls-and-gateway.md` | TLS/mTLS、网关（如 Envoy）的操作步骤与证书约定 |
| `security/api-access.md` | HTTP API 鉴权、简易 Web UI 的认证方式 |

**侧栏分组名建议**：网络与安全

---

### 3.4 存储与数据面 `storage/`

| 建议路径 | 内容要点 |
|----------|----------|
| `storage/object-store-model.md` | 预签名 URL、直传、**桶由运维预创建**等产品约定 |
| `storage/large-objects.md` | 分片上传、重试、恢复侧流式与校验（与实现一致） |
| `storage/tuning.md` | 阈值类环境变量与调优建议 |

**侧栏分组名建议**：存储与数据面

---

### 3.5 使用指南 `guides/`

| 建议路径 | 内容要点 |
|----------|----------|
| `guides/backup-and-restore.md` | 端到端：创建任务 → 查询状态 → 恢复路径 |
| `guides/policies-and-schedules.md` | 策略与 Cron 定时语义、并发锁等行为 |
| `guides/web-console.md` | 简易 UI 能力边界与操作说明 |

**侧栏分组名建议**：使用指南

---

### 3.6 参考 `reference/`

| 建议路径 | 内容要点 |
|----------|----------|
| `reference/http-api.md` | 如何打开 Swagger、重要资源路径；后续可选接入 OpenAPI 插件 |
| `reference/grpc-services.md` | Agent 侧 gRPC 能力概述；指向仓库内 `proto/` 或生成文档 |
| `reference/ports-and-paths.md` | 端口、HTTP 路由、容器内挂载路径等速查表 |

**侧栏分组名建议**：参考

---

### 3.7 开发与贡献 `development/`

| 建议路径 | 内容要点 |
|----------|----------|
| `development/local-setup.md` | 克隆、虚拟环境、`pip install -e .[dev]`、常用命令 |
| `development/project-structure.md` | `src/`、`deploy/`、`proto/` 等目录职责 |
| `development/testing.md` | pytest、gRPC 相关注意点 |
| `development/releasing.md` | 版本号策略、`CHANGELOG.md` 维护约定 |

**侧栏分组名建议**：开发与贡献  

页脚建议链接：`CONTRIBUTING`、`SECURITY`、`LICENSE`（若仓库中存在）。

---

### 3.8 可选内容

- **Blog**（`blog/`）：发版说明、破坏性变更迁移短文，与 `CHANGELOG` 互补。
- **路线图**：例如 `intro/roadmap.md` 或 `intro/future-direction.md`，单独撰写当前产品方向即可。

---

## 4. Docusaurus 实现要点（备忘）

- **`sidebars.ts`**：按上文章节建立多个侧栏分组；组内文档 id 显式列出，顺序即推荐阅读顺序。
- **Front matter**：每篇至少 `title`、`description`；同组内用 `sidebar_position` 控制排序。
- **首页**：`src/pages/index.md`（或自定义 React 首页）：价值主张 + 指向「文档」与「GitHub」的 CTA。
- **不启用**向旧 URL 的 redirect（本方案明确不要求向后兼容）。
- **路由前缀**：默认文档在 `/docs/...`。若希望文档占站点根路径，可在配置中将 docs 的 `routeBasePath` 设为 `'/'`，并相应设置 `baseUrl`（需与托管环境一致）。

---

## 5. 根 README 与文档站的关系（落地时检查）

- 根 `README.md`：保留最短「如何起服务」与端口速览 + **唯一**「完整文档 → 文档站 URL」。
- 不再在 README 中维护与旧 `docs/*.md` 路径绑定的长链列表（避免与已归档目录混淆）。

---

## 6. 刻意不做的约定（与「从零」一致）

- 不把 `docs-old` 作为线上文档源或 symlink。
- 站内不写「见 docs-old」或旧文件名映射说明。
- 需要保留的历史信息应在 **`website/docs/` 新路径下重写** 并入对应章节。

---

## 7. 后续构建清单（实现阶段）

1. `npx create-docusaurus@latest website classic --typescript`（或等价初始化）。
2. 在 `website/docs/` 下按第 3 节创建目录与占位/正式文稿。
3. 编写 `sidebars.ts` 与 `docusaurus.config.ts`（`url`、`baseUrl`、`editUrl`、navbar、footer）。
4. 更新根 `README.md` 文档链接。
5. CI：对 `website/` 执行 `npm ci` + `npm run build`；主分支部署到 GitHub Pages / Vercel 等（按项目选择）。

---

## 8. 实现状态（仓库内）

- 正式文档站位于仓库根目录 **`website/`**（`docs/` 为站内 Markdown 根，**不是**本 `docs-old` 目录）。
- 使用说明见 **`website/README.md`**；本地构建已通过 `npm run build` 校验。
- CI：`.github/workflows/docs.yml` 在变更 `website/**` 时执行 `npm ci` 与 `npm run build`。

---

*本文档版本：与仓库内首次落盘时一致；若 IA 有调整，请直接修改本文件并同步更新 `website/docs/` 与 `sidebars.ts`，以免与实现漂移。*
