# DeVault

面向企业交付的**备份与恢复**平台：控制面（HTTP API、gRPC、PostgreSQL、Redis）与边缘 Agent（gRPC + S3 兼容存储）分离，Pull 模型调度，支持策略与 Cron、任务取消/重试、Prometheus 与简易 Web UI。

> 默认根 **README** 为英文，见 [`README.md`](README.md)。

## 快速开始

在仓库根目录，**不加 profile** 时仅启动内置 **Postgres / Redis / MinIO / minio-init**：

```bash
cd deploy
docker compose pull && docker compose up -d
```

要启动 **IAM、api、scheduler** 以及可选 **agent / 控制台**，需启用 Compose **profile**，例如与 **`install.sh`** 默认一致（控制面 + Agent）：

```bash
cd deploy
docker compose pull && docker compose --profile with-control-plane --profile with-agent up -d
```

**api** 运行后可在本机访问 **Swagger**：<http://127.0.0.1:8000/docs>；迁移在 **api** 启动时执行（`alembic upgrade head`）。profile 说明见 **`deploy/docker-compose.yml`** 文件头与网站文档 **Docker Compose** 章节。

`docker-compose.yml` 中 **api / scheduler / agent** 同时声明了 **`image`**（默认 **`glf9832/devault:latest`**）与 **`build`**（`deploy/Dockerfile`）。带 profile 的 **`pull && up -d`** 使用预拉取镜像；加上 **`--build`** 或执行 **`make demo-stack-up`** 会从源码构建 **`devault:local`**（及控制台镜像）。环境变量模板见 **`deploy/.env.stack.example`**（可复制为 **`deploy/.env`**）。

### 远程一键安装（无需 `git clone`）

官方仓库：**[skyline93/devault](https://github.com/skyline93/devault)**。脚本从对应 raw 路径拉取 `docker-compose.yml`，在**当前目录**启动（可用 `--dir` 指定目录）。默认拉取 **Docker Hub** `glf9832/devault:latest-<amd64|arm64>`（由 `uname -m` 决定）；只有需要其它镜像时才设置 **`DEVAULT_IMAGE`**（完整引用）。

```bash
curl -fsSL https://raw.githubusercontent.com/skyline93/devault/main/deploy/scripts/install.sh | sh
```

可选：`DEVAULT_REF` 指定分支或 tag（默认 `main`）以固定所拉取的 `deploy/` 版本；仅在镜像了 `deploy/` 目录时才需要 `DEVAULT_INSTALL_BASE_URL`。**`DEVAULT_COMPOSE_PROFILES`** 可覆盖默认 **`COMPOSE_PROFILES`**（默认 **`with-control-plane,with-agent`**，安装后即有 **Swagger**）。更多见 `deploy/scripts/install.sh` 头部注释。

**本地克隆**：执行 `./deploy/scripts/install.sh` 会在仓库的 **`deploy/`** 目录内先 **`compose pull`** 再带默认 profile 的 **`up -d`**；`--dir` 在此模式下会被忽略。

维护者：GitHub Actions 密钥 `DOCKERHUB_USERNAME`、`DOCKERHUB_TOKEN`（一般为拥有 `glf9832/devault` 的 Docker Hub 账号），可选仓库变量 `DOCKERHUB_IMAGE` 以推送其它镜像名。工作流：`.github/workflows/docker-publish.yml`（默认推送 `glf9832/devault`）。

**本地构建 / 推送（不走 CI）：** 在仓库根目录执行 `make help` 查看镜像相关目标，例如：

```bash
make docker-build-push
make docker-buildx-push IMAGE=glf9832/devault:latest
```

推送前先对目标仓库执行 `docker login`。可选：`PLATFORMS=linux/arm64` 做单架构 buildx `--load`；`docker-buildx-push` 可通过 `PLATFORMS_MULTI` 覆盖默认多架构列表。

## 文档

- **完整用户与运维说明**：[文档站源码](website/)，正文在 [`website/docs/`](website/docs/index.md)。本地预览：`cd website && npm ci && npm start` → <http://localhost:3000>
- **控制面 ↔ Agent 兼容矩阵**（机器可读）：[`docs/compatibility.json`](docs/compatibility.json)
- **发版记录**：[`docs/RELEASE.md`](docs/RELEASE.md)

API 端点、gRPC/TLS、S3 与 Helm 等细节见文档站对应章节，不再在根 README 展开。

## 仓库结构（节选）

| 目录 | 说明 |
|------|------|
| `Makefile` | 本地 `docker build` / `push`（`make help`） |
| `src/devault/` | 控制面与 Agent 相关 Python 包 |
| `deploy/` | `docker-compose.yml`、`scripts/install.sh`、镜像、Helm Chart、Agent 示例挂载目录 `demo_data/` |
| `website/` | Docusaurus 文档站 |
| `console/` | Ant Design Pro（Umi 4）企业控制台 |
| `tests/` | pytest |
| `openspec/` | [OpenSpec](https://github.com/Fission-AI/OpenSpec) 规格与变更目录（`specs/` 基线、`changes/` 进行中与归档） |
| `.cursor/` | Cursor 的 OpenSpec 斜杠命令与 Skills（`make openspec-update` 可刷新） |

## OpenSpec（AI 规格驱动开发）

本仓库已接入 **OpenSpec**，用于在写代码前与 AI 对齐「做什么、怎么做、如何验收」。

- **环境**：需要 **Node.js ≥ 20.19**；CLI 可全局安装 `npm i -g @fission-ai/openspec`，或在仓库根使用 `npx @fission-ai/openspec@latest <子命令>`。
- **在 Cursor 里**：重启或重新加载窗口后，可使用 **`/opsx:propose`**、**`/opsx:apply`**、**`/opsx:archive`**、**`/opsx:explore`**（定义见 `.cursor/commands/` 与 `.cursor/skills/`）。
- **刷新指令**：升级 `@fission-ai/openspec` 后在仓库根执行 **`make openspec-update`**（已设置 `OPENSPEC_TELEMETRY=0`）。
- **遥测**：也可设置 `DO_NOT_TRACK=1` 关闭统计（见 [OpenSpec README](https://github.com/Fission-AI/OpenSpec)）。
- **更多工作流**（如 `/opsx:verify`）：在终端交互运行 `openspec config profile` 后执行 `openspec update` 或 `make openspec-update`。

官方文档：[Getting Started](https://github.com/Fission-AI/OpenSpec/blob/main/docs/getting-started.md)。

## 本地开发（摘要）

需要 **Python ≥ 3.12**、PostgreSQL、Redis 与 S3 兼容端点（与生产 Agent 预签名一致）。安装与运行示例见文档站 **运维 / 安装** 类页面；常用命令：

```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
alembic upgrade head
pytest -q
```

修改 `proto/agent.proto` 后执行 `bash scripts/gen_proto.sh`（需 `grpcio-tools`）。

## 许可证

MIT（可按需在仓库根目录补充 `LICENSE` 文件）。
