---
sidebar_position: 3
title: 数据库迁移
description: Alembic 升级与多实例注意事项
---

# 数据库迁移

DeVault 使用 **Alembic** 管理 PostgreSQL 架构变更。

## 首次与升级

在可访问数据库的环境中执行：

```bash
alembic upgrade head
```

Docker Compose 下 **`api` 服务**在启动脚本中执行上述命令，因此拉起 `api` 即会迁移到最新版本。

## 为何 scheduler 不跑迁移

历史上多容器同时执行 `alembic upgrade` 可能在 `alembic_version` 等对象上产生竞态。当前约定：

- **仅 `api`** 在启动时执行 `alembic upgrade head`
- **`scheduler`** 不执行迁移

自建编排时，请保持「**单一迁移责任**」：任选一种方式——仅一个 Job 迁移、或独立迁移 Job 完成后才扩容 API ——避免并发迁移。

## 本地开发

与 [本地开发环境](../development/local-setup.md) 相同：先导出 `DEVAULT_DATABASE_URL`，再 `alembic upgrade head`，最后启动 `uvicorn`。
