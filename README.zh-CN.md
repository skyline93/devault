# DeVault

面向企业交付的**备份与恢复**平台：控制面（HTTP API、gRPC、PostgreSQL、Redis）与边缘 Agent（gRPC + S3 兼容存储）分离，Pull 模型调度，支持策略与 Cron、任务取消/重试、Prometheus 与简易 Web UI。

> 默认根 **README** 为英文，见 [`README.md`](README.md)。

## 快速开始

在仓库根目录执行：

```bash
cd deploy
docker compose up --build -d
```

启动后可在本机访问 **Swagger**：<http://127.0.0.1:8000/docs>。数据库迁移在 Compose 中由 **api** 服务在启动时执行（`alembic upgrade head`）。

## 文档

- **完整用户与运维说明**：[文档站源码](website/)，正文在 [`website/docs/`](website/docs/index.md)。本地预览：`cd website && npm ci && npm start` → <http://localhost:3000>
- **控制面 ↔ Agent 兼容矩阵**（机器可读）：[`docs/compatibility.json`](docs/compatibility.json)
- **发版记录**：[`docs/RELEASE.md`](docs/RELEASE.md)

API 端点、gRPC/TLS、S3 与 Helm 等细节见文档站对应章节，不再在根 README 展开。

## 仓库结构（节选）

| 目录 | 说明 |
|------|------|
| `src/devault/` | 控制面与 Agent 相关 Python 包 |
| `deploy/` | Docker Compose、镜像与 Helm Chart |
| `website/` | Docusaurus 文档站 |
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
