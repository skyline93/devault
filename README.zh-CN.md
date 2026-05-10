# DeVault

面向企业交付的**备份与恢复**平台：控制面（HTTP API、gRPC、PostgreSQL、Redis）与边缘 Agent（gRPC + S3 兼容存储）分离，Pull 模型调度，支持策略与 Cron、任务取消/重试、Prometheus 与简易 Web UI。

> 默认根 **README** 为英文，见 [`README.md`](README.md)。

## 快速开始

在仓库根目录执行：

```bash
cd deploy
docker compose pull && docker compose up -d
```

启动后可在本机访问 **Swagger**：<http://127.0.0.1:8000/docs>。数据库迁移在 Compose 中由 **api** 服务在启动时执行（`alembic upgrade head`）。

`docker-compose.yml` **仅使用预构建镜像**（api / scheduler / agent 的 **`image: ${DEVAULT_IMAGE:-glf9832/devault:latest}`**）。更换仓库或标签请设置 **`DEVAULT_IMAGE`**。镜像需用 **`Makefile`**、CI 或 `docker build` 单独构建；Compose 中**没有** `build` 段。

### 远程一键安装（无需 `git clone`）

官方仓库：**[skyline93/devault](https://github.com/skyline93/devault)**。脚本从对应 raw 路径拉取 `docker-compose.yml`，在**当前目录**启动（可用 `--dir` 指定目录）。默认拉取 **Docker Hub** `glf9832/devault:latest-<amd64|arm64>`（由 `uname -m` 决定）；只有需要其它镜像时才设置 **`DEVAULT_IMAGE`**（完整引用）。

```bash
curl -fsSL https://raw.githubusercontent.com/skyline93/devault/main/deploy/scripts/install.sh | sh
```

可选：`DEVAULT_REF` 指定分支或 tag（默认 `main`）以固定所拉取的 `deploy/` 版本；仅在镜像了 `deploy/` 目录时才需要 `DEVAULT_INSTALL_BASE_URL`。更多见 `deploy/scripts/install.sh` 头部注释。

**本地克隆**：执行 `./deploy/scripts/install.sh` 会在仓库的 **`deploy/`** 目录内先 **`compose pull`** 再 **`up -d`**；`--dir` 在此模式下会被忽略。

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
