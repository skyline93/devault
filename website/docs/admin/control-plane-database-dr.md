---
sidebar_position: 9
title: 控制面元数据库备份与 DR
description: PostgreSQL 逻辑备份、可选 PITR、RTO/RPO
---

# 控制面元数据库备份与 DR

本文档针对 **控制面所使用的 PostgreSQL**（租户、策略、任务、artifact 元数据、API 密钥哈希等）。**不包含**对象存储中的 bundle/manifest（见 [备份与恢复流程](../user/backup-and-restore.md)）。

## 术语

| 概念 | 说明 |
|------|------|
| **逻辑备份** | `pg_dump` / `pg_restore` |
| **物理备份 / PITR** | 基础备份 + WAL 归档 |
| **RPO / RTO** | 数据丢失容忍与恢复耗时目标（由 SLA 定义） |

| 策略 | 典型 RPO | 典型 RTO | 备注 |
|------|-----------|-----------|------|
| 每日逻辑备份 + 异地拷贝 | ~24h | 分钟～小时 | 与本仓库脚本一致 |
| 每小时逻辑备份 | ~1h | 同上 | |
| WAL 归档 + PITR | 分钟～秒级 | 依赖回放速度 | RDS 等常内置 |
| 流复制热备 | 近 0 | 切换较短 | 超出本脚本范围 |

## 逻辑备份（Compose）

脚本 **`deploy/scripts/control-plane-pg-backup.sh`**（`-Fc`）。

```bash
mkdir -p backups
./deploy/scripts/control-plane-pg-backup.sh -o "./backups/control-plane-$(date +%Y%m%d-%H%M%S).dump" --compose-dir ./deploy
```

可选 **`-f`** 指定 Compose 文件名。

等价：

```bash
cd deploy
docker compose exec -T postgres pg_dump -U devault -d devault -Fc > ../backups/manual.dump
```

## 逻辑恢复

执行前：**停止写入**（停 **api**、**scheduler**），设置 **`DEVAULT_PG_RESTORE_CONFIRM=yes`**，恢复后视需要 **`alembic upgrade head`**。

```bash
export DEVAULT_PG_RESTORE_CONFIRM=yes
./deploy/scripts/control-plane-pg-restore.sh \
  -i ./backups/control-plane-20260509.dump \
  --compose-dir ./deploy \
  --restart-services
```

## PITR 概要

逻辑备份无法恢复到备份间隔内的任意一秒。连续保护需在 PostgreSQL 层启用 WAL 归档、基础备份与按时间点恢复；云托管 RDS/Cloud SQL 等常提供时间点还原。

详见 [PostgreSQL 连续归档与恢复](https://www.postgresql.org/docs/current/continuous-archiving.html)。

## 与对象存储、密钥

- **仅恢复 PostgreSQL** 不会恢复被删的 **S3 对象**。
- **`control_plane_api_keys`** 仅存 SHA256，明文密钥不可从 DB 逆推。
- Artifact 对称密钥在 Agent 侧配置。

## 演练清单（建议季度）

隔离环境还原最近备份 → 启动兼容镜像 → **`/healthz`** → 抽样核对元数据 → 记录耗时与 RTO。

## 脚本

| 文件 | 作用 |
|------|------|
| `deploy/scripts/control-plane-pg-backup.sh` | `pg_dump -Fc` |
| `deploy/scripts/control-plane-pg-restore.sh` | `pg_restore` + 可选 Compose 停启 |
