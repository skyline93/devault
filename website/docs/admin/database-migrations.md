---
sidebar_position: 7
title: 数据库迁移
description: Alembic 升级与多实例注意事项
---

# 数据库迁移

DeVault 使用 **Alembic** 管理 PostgreSQL 架构。

## 首次与升级

```bash
alembic upgrade head
```

Docker Compose 下 **`api`** 启动脚本包含上述命令。

## scheduler 不跑迁移

约定：

- **仅 `api`** 在启动时执行 `alembic upgrade head`
- **`scheduler`** 不执行迁移

自建编排保持 **单一迁移责任**，避免并发 `alembic`。

控制面 **PostgreSQL** 的备份与 PITR 见 [控制面元数据库备份与 DR](./control-plane-database-dr.md)。表级关系见工程文档 [控制面数据库 ER 图](../engineering/control-plane-database-er.md)。

## 本地开发

导出 `DEVAULT_DATABASE_URL` 后 `alembic upgrade head`，再启动 `uvicorn`（见 [本地开发](../engineering/local-setup.md)）。
