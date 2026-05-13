---
sidebar_position: 2
title: 本地开发环境
description: 虚拟环境、依赖与常用进程
---

# 本地开发环境

## 克隆与虚拟环境

```bash
git clone <你的仓库 URL>
cd devault
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## 依赖服务

**PostgreSQL**、**Redis**、（完整 Agent 路径）**S3 兼容存储**。

## 启动 API（示例）

```bash
export DEVAULT_DATABASE_URL=postgresql+psycopg://devault:devault@localhost:5432/devault
export DEVAULT_REDIS_URL=redis://localhost:6379/0
export DEVAULT_API_TOKEN=dev
export DEVAULT_STORAGE_CONFIG_MASTER_KEY='<fernet-key-from-cryptography.fernet.Fernet.generate_key>'
# 迁移不会插入默认 storage profile；在控制台创建并激活 profile（S3 或 local）后再跑备份。
export DEVAULT_GRPC_LISTEN=0.0.0.0:50051

alembic upgrade head
uvicorn devault.api.main:app --reload --port 8000
```

## 启动 Agent（另一终端）

```bash
export DEVAULT_API_TOKEN=dev
export DEVAULT_GRPC_TARGET=127.0.0.1:50051
export DEVAULT_ALLOWED_PATH_PREFIXES=/data,/restore
devault-agent
```

单测可配合 fixture 插入并激活 **`storage_type=local`** 的 profile，以缩短本地路径。
