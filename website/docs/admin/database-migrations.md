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

## 生成新迁移

在**空库或已与模型对齐的库**上，对照当前 ORM 生成迁移脚本（`alembic.ini` 已配置按时间排序的 **`file_template`**，便于版本目录排序）：

```bash
export DEVAULT_DATABASE_URL=postgresql+psycopg://...
alembic revision --autogenerate -m "short_description"
```

生成后请人工审阅 diff（索引、`server_default`、PostgreSQL 专有类型等）。**IAM** 迁移见 [`iam/README.md`](../../../iam/README.md) 数据库章节。
