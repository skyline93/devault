---
sidebar_position: 4
title: 控制面元数据库备份与灾难恢复
description: PostgreSQL 逻辑备份、可选 PITR、RTO/RPO 与 Compose 脚本示例
---

# 控制面元数据库备份与灾难恢复（Runbook）

本文档针对 **DeVault 控制面所使用的 PostgreSQL**：存放租户、策略、任务、artifact 元数据、API 密钥哈希等。**不包含**对象存储中的备份 bundle/manifest（那是「数据面」产物；端到端备份/恢复流程见 [备份与恢复流程](../guides/backup-and-restore.md)）。

运维目标：

- **元数据库丢失**时，能用备份重建控制面 schema 与业务元数据（前提：对象存储中的对象仍存在且键未被手动打乱）。
- **误删或损坏**时，可按恢复流程回滚到某一备份点；更严格的连续保护依赖 **WAL 归档与 PITR**（见下文）。

---

## 术语与范围

| 概念 | 说明 |
|------|------|
| **逻辑备份** | `pg_dump` / `pg_restore`，导出 SQL 对象与数据；实施简单，适合定期快照与跨版本迁移演练。 |
| **物理备份 / PITR** | 基础备份 + WAL 日志归档，可将实例恢复到任意时间点（依赖 PostgreSQL 连续归档与恢复配置）。 |
| **RPO**（Recovery Point Objective） | 能接受丢失多长时间的**数据变更**（例如最后一次逻辑备份时刻，或 WAL 回放精度）。 |
| **RTO**（Recovery Time Objective） | 能接受多长**停机**完成切换或恢复（停 API、恢复库、校验、再起服务）。 |

以下 **RTO/RPO 表为规划占位**：请在贵司 SLA 中写明数值；技术上下界取决于采用的是「仅逻辑备份」还是「PITR + 高可用」。

| 策略 | 典型 RPO | 典型 RTO | 备注 |
|------|-----------|-----------|------|
| 每日逻辑备份 + 异地拷贝 | 最长 ~24h（未额外同步事务日志） | 恢复窗口 + 人工介入（分钟～小时级） | 适合中小规模控制面；与本仓库脚本一致。 |
| 每小时逻辑备份 + 监控告警 | ~1h | 同上 | 缩小备份间隔可改善 RPO，仍非连续。 |
| WAL 归档 + `recovery_target_time`（PITR） | 分钟级～秒级（取决于归档延迟） | 取决于存储回放速度与演练熟练度 | 需在 PostgreSQL 层启用归档与基础备份流程；云托管 RDS/Aurora 常内置连续备份。 |
| 流复制热备 | 接近 0（异步副本略滞后） | 切换通常低于全库 restore | 运维复杂度更高，超出本 Runbook 脚本范围。 |

---

## 逻辑备份（推荐基线）

### 前置条件

- 生产环境应使用专用数据库账号与最小权限；备份账号至少需要目标库的 **读权限**（`pg_dump`）。
- **一致性**：高写入负载下，`pg_dump` 默认提供一致快照（单个快照语义）；极端并发下仍建议在低峰执行或使用复制副本上备份（需处理滞后）。

### 使用仓库脚本（Docker Compose）

脚本路径：**`deploy/scripts/control-plane-pg-backup.sh`**（自定义格式 `-Fc`）。

自仓库根目录、已启动 `deploy/docker-compose.yml` 栈：

```bash
mkdir -p backups
./deploy/scripts/control-plane-pg-backup.sh -o "./backups/control-plane-$(date +%Y%m%d-%H%M%S).dump" --compose-dir ./deploy
```

可选：若 Compose 主文件不是默认 `docker-compose.yml`，在两脚本上均可使用 **`-f`**：

```bash
./deploy/scripts/control-plane-pg-backup.sh -o ./backups/cp.dump --compose-dir ./deploy -f docker-compose.grpc-tls.yml
```

### 不使用脚本（等价命令）

```bash
cd deploy
docker compose exec -T postgres pg_dump -U devault -d devault -Fc > ../backups/manual.dump
```

### 直连集群（本机 `pg_dump`）

```bash
export PGHOST=... PGPORT=5432 PGUSER=... PGPASSWORD=... PGDATABASE=devault
./deploy/scripts/control-plane-pg-backup.sh -o ./backups/cp.dump
```

---

## 逻辑恢复

恢复会 **覆盖** 当前库中与备份冲突的对象；执行前必须：

1. **停止对同一库的写入**：至少停止 **HTTP API** 与 **scheduler**（以及任何直连 DB 的迁移任务），避免与 `pg_restore --clean` 争抢连接。
2. 确认 **`DEVAULT_PG_RESTORE_CONFIRM=yes`**（脚本强制门禁）。
3. 若当前应用镜像 **新于** 备份时的迁移版本，恢复后执行 **`alembic upgrade head`**（通常由 `api` 容器启动脚本完成；自建编排时请单独跑迁移）。

### 使用仓库脚本（Compose + 可选自动停启）

```bash
export DEVAULT_PG_RESTORE_CONFIRM=yes
./deploy/scripts/control-plane-pg-restore.sh \
  -i ./backups/control-plane-20260509.dump \
  --compose-dir ./deploy \
  --restart-services
```

`--restart-services` 会在恢复前后对 **`api`** 与 **`scheduler`** 执行 `stop` / `start`（适用于默认 `deploy/docker-compose.yml` 服务名）。非默认 Compose 主文件时增加 **`-f my-compose.yml`**。若你叠加了其它 Compose 文件或改名服务，请改为手工停启对应工作负载。

### 手工步骤摘要

1. `docker compose stop api scheduler`（或等价编排）。
2. 将 `.dump` 拷入 postgres 容器或使用 `docker compose cp`。
3. `pg_restore -U ... -d devault --clean --if-exists --no-owner --no-acl -v /path/in/container.dump`
4. `docker compose start api scheduler`
5. 校验 **`GET /healthz`**、抽样查询任务与 artifact 列表。

---

## 时间点恢复（PITR）概要

逻辑备份无法恢复到「两次备份之间的某一秒」。若企业要求 **分钟级 RPO**，请在 PostgreSQL 层启用：

1. **WAL 归档**：`archive_mode = on`，`archive_command` 将 WAL 段推到对象存储或 NFS（权限与加密按贵司标准）。
2. **基础备份**：定期 `pg_basebackup`（或云厂商快照）+ 保留周期策略。
3. **恢复**：新实例上配置 `restore_command` 与 `recovery_target_time`（或 `recovery_target_xid`），回放 WAL 至目标时刻。

云托管数据库（RDS、Cloud SQL、Azure Database for PostgreSQL 等）通常提供 **自动备份 + 按时间点还原**，可直接作为控制面元库的 **PITR** 方案；此时 Runbook 中的 Shell 脚本仍可用于 **逻辑导出演练** 或迁出数据。

详细参数请查阅 [PostgreSQL 官方文档：连续归档与时间线恢复](https://www.postgresql.org/docs/current/continuous-archiving.html)。

---

## 与对象存储、密钥的关系

- **仅恢复 PostgreSQL** 不会重建丢失的 **S3 对象**。若桶被清空，还需依赖对象存储侧的 **版本控制 / 跨区域复制 / 服务商备份**。
- **Redis**（会话锁等）通常可按空实例重启；如有自定义持久化需求请单独备份。
- **`control_plane_api_keys` 存 SHA256**，原始密钥不可从 DB 逆推；恢复后仍是同一哈希，已发放的明文密钥需自行保管。
- **Artifact 加密**：密钥在 Agent 侧（`DEVAULT_ARTIFACT_ENCRYPTION_KEY`）；元数据库恢复与密钥管理无关。

---

## 演练清单（建议每季度）

1. 在隔离环境还原最近一次逻辑备份。
2. 启动兼容版本的控制面镜像，确认 **`alembic`** 状态与 **`/healthz`**。
3. 核对租户、策略、任务与 artifact **元数据** 是否与预期一致（抽样即可）。
4. 记录实际耗时，更新贵司内部 **RTO** 估计与值班手册。

---

## 脚本路径速查

| 文件 | 作用 |
|------|------|
| `deploy/scripts/control-plane-pg-backup.sh` | `pg_dump -Fc` 逻辑备份 |
| `deploy/scripts/control-plane-pg-restore.sh` | `pg_restore` +（可选）Compose 停写 |
