#docs

# DeVault 项目设计文档

> **开发实现与排期**：若以「先文件备份、后数据库备份」落地，请参阅 [开发设计文档（文件备份优先版）](./development-design.md)。

## 一、项目背景

### 1.1 项目定位

DeVault 是一个面向开发者、小团队、自托管用户（Self-hosted）以及 Homelab 场景的数据备份与恢复平台。

项目目标并不是构建一个传统企业级复杂备份系统，而是提供一个：

* 开发者真正愿意使用
* 可以本地部署
* 对 Docker / 数据库友好
* 支持自动化备份与恢复
* 具备现代云原生能力
* 易于扩展与二次开发

的轻量级数据保护平台。

项目重点体现：

* Python 后端工程能力
* 分布式任务调度能力
* 数据基础设施能力
* 容器化与 Kubernetes 实践能力
* 系统设计与工程化能力
* 稳定性与可观测性设计能力

---

# 二、项目目标

## 2.1 核心目标

DevVault 主要解决开发者日常中的以下问题：

### 数据安全

* 本地 PostgreSQL/MySQL 数据如何自动备份
* Docker Volume 如何备份
* 如何快速恢复开发环境
* 如何做历史版本回滚

### 开发环境迁移

* 如何迁移开发数据
* 如何在多设备之间同步
* 如何在云主机/NAS 间恢复

### 自动化管理

* 自动定时备份
* 自动清理过期备份
* 失败自动重试
* 备份状态追踪

### 可观测性

* 查看任务执行日志
* 查看备份耗时
* 查看失败原因
* 查看系统运行状态

---

# 三、目标用户

## 3.1 用户画像

### 独立开发者

* 本地开发环境备份
* Docker Compose 项目备份
* SQLite/PostgreSQL 数据恢复

### 小型创业团队

* 测试环境数据保护
* 自动恢复演练
* 开发环境统一管理

### Homelab / NAS 用户

* 家庭服务器备份
* 自托管服务备份
* MinIO/NAS 数据归档

### Python 后端开发者

* 可作为二次开发平台
* 插件式扩展数据库支持

---

# 四、项目核心功能

# 4.1 数据源支持

## 数据库支持

第一阶段：

* PostgreSQL
* MySQL
* Redis

第二阶段：

* MongoDB
* SQLite
* Elasticsearch

---

# 4.2 备份功能

## 全量备份

支持：

* pg_dump
* mysqldump
* Redis RDB/AOF

功能包括：

* 压缩
* 加密
* 分片上传
* 校验

---

## 增量备份（第二阶段）

支持：

* PostgreSQL WAL
* MySQL Binlog

实现：

* 时间点恢复（PITR）
* 增量归档
* 自动恢复链构建

---

# 4.3 恢复功能

## 一键恢复

支持：

* 恢复到新实例
* 恢复到指定时间点
* 临时恢复演练

支持：

* Docker 容器恢复
* 本地目录恢复
* Kubernetes Job 恢复

---

# 4.4 Docker 集成

## 自动发现能力

自动扫描：

* Docker 容器
* Docker Compose
* Docker Volume

示例：

```bash
$ devvault scan

发现以下服务：
- postgres-dev
- redis-cache
- mysql-test

是否加入自动备份计划？
```

---

## Docker Volume 备份

支持：

* Volume Snapshot
* Volume Restore
* Volume Diff

---

# 4.5 存储支持

## 本地存储

支持：

* 本地磁盘
* NAS 挂载目录

---

## 对象存储

支持：

* MinIO
* Amazon S3
* 阿里云 OSS（后期）
* 腾讯云 COS（后期）

功能：

* 分片上传
* 生命周期管理
* 自动归档

---

# 4.6 调度系统

## 定时任务

支持：

* Cron 表达式
* 周期调度
* 手动触发

例如：

```yaml
jobs:
  - name: postgres-backup
    type: postgres
    schedule: "0 */6 * * *"
```

---

## 任务状态机

任务状态：

```text
PENDING
RUNNING
UPLOADING
VERIFYING
SUCCESS
FAILED
RETRYING
```

---

## 重试机制

支持：

* 自动 retry
* 指数退避
* 超时控制
* 死信任务

---

# 4.7 Web UI

## 功能

### Dashboard

显示：

* 最近备份
* 失败任务
* 存储占用
* 数据趋势

### 任务管理

支持：

* 创建备份任务
* 手动执行
* 查看日志
* 删除历史备份

### 恢复管理

支持：

* 选择历史快照
* 一键恢复
* 临时恢复环境

---

# 4.8 CLI 工具

项目提供 CLI 工具：

```bash
devvault backup postgres
```

```bash
devvault restore backup-id
```

```bash
devvault scan
```

```bash
devvault status
```

CLI 是项目的重要组成部分。

用于体现：

* 开发者工具产品化能力
* 用户体验设计能力
* 自动化运维能力

---

# 4.9 可观测性

## Metrics

基于 Prometheus：

指标包括：

* backup_duration_seconds
* backup_success_total
* backup_failed_total
* storage_usage_bytes

---

## 日志

统一日志系统：

* structured logging
* trace_id
* task_id

支持：

* Loki
* ELK

---

## Tracing

基于 OpenTelemetry：

* API Trace
* Worker Trace
* Storage Trace

---

# 五、系统架构设计

# 5.1 总体架构

```text
                 +----------------+
                 |     Web UI     |
                 +--------+-------+
                          |
                     REST API
                          |
+------------------------------------------------+
|             FastAPI API Server                 |
| auth / backup / restore / schedule / metadata  |
+------------------------------------------------+
             |                     |
             |                     |
        PostgreSQL             Redis
             |
             |
+------------------------------------------------+
|               Scheduler Service                |
| cron / retry / state machine                   |
+------------------------------------------------+
             |
             |
+---------------- Message Queue -----------------+
             |
     +-------+-------+-------+
     |               |       |
+----------+   +----------+  +----------+
| Worker1  |   | Worker2  |  | WorkerN  |
+----------+   +----------+  +----------+
      |
      |
+-----------------------------------------------+
| Backup Plugins                                |
| postgres / mysql / redis / docker volume      |
+-----------------------------------------------+
      |
      |
+-----------------------------------------------+
| Storage Backend                               |
| local / MinIO / S3                            |
+-----------------------------------------------+
```

---

# 六、技术栈设计

# 6.1 后端框架

## FastAPI

用途：

* REST API
* OpenAPI 文档
* 后台管理接口

原因：

* async 支持优秀
* Python 现代化生态
* 自动生成 API 文档
* 高性能

---

# 6.2 ORM

## SQLAlchemy 2.0

用途：

* 元数据管理
* 任务状态管理
* Backup Record 管理

体现能力：

* ORM 建模
* 数据关系设计
* Repository Pattern

---

# 6.3 分布式任务系统

## Celery + Redis

用途：

* 异步任务调度
* Backup Worker
* Restore Worker
* Retry 机制

体现能力：

* 分布式任务系统
* 并发控制
* 幂等设计
* retry 策略

---

# 6.4 调度系统

## APScheduler

用途：

* Cron 调度
* 周期任务管理

体现能力：

* 任务编排
* 调度体系设计

---

# 6.5 数据库

## PostgreSQL

用途：

* 平台元数据存储
* Backup 元数据管理
* Task State 管理

---

# 6.6 缓存与队列

## Redis

用途：

* Celery Broker
* 缓存
* 分布式锁

---

# 6.7 容器化

## Docker

用途：

* 服务部署
* Worker 部署
* 本地开发环境

---

## Kubernetes

用途：

* Worker 弹性扩容
* Backup Job 隔离执行
* Helm 部署

体现能力：

* 云原生部署能力
* 容器化架构能力
* Kubernetes 运维能力

---

# 6.8 对象存储

## MinIO

用途：

* Backup Artifact Storage
* 本地对象存储模拟

体现能力：

* S3 协议
* 对象存储链路

---

# 6.9 可观测性

## Prometheus

* Metrics 收集
* SLA 统计

## Grafana

* Dashboard
* Backup 趋势分析

## OpenTelemetry

* Trace 链路追踪

体现能力：

* 生产级系统可观测性设计

---

# 七、核心模块设计

# 7.1 Plugin 插件系统

## 设计目标

支持：

* 数据库扩展
* 存储扩展
* 恢复扩展

---

## 插件接口

```python
class BackupPlugin:
    async def backup(self):
        pass

    async def restore(self):
        pass

    async def verify(self):
        pass
```

体现能力：

* 插件化架构设计
* 面向接口编程
* 可扩展系统设计

---

# 7.2 Worker 执行模型

## 设计目标

解决：

* 长任务执行
* 并发隔离
* 重试恢复
* 状态追踪

---

## 执行流程

```text
API -> Scheduler -> Celery Queue -> Worker
```

---

# 7.3 状态机设计

## Backup State

```text
PENDING
RUNNING
UPLOADING
VERIFYING
SUCCESS
FAILED
RETRYING
```

体现能力：

* 复杂任务流设计
* 分布式任务状态控制

---

# 7.4 存储抽象层

## Storage Interface

```python
class StorageBackend:
    async def upload(self):
        pass

    async def download(self):
        pass

    async def delete(self):
        pass
```

支持：

* LocalStorage
* MinIOStorage
* S3Storage

体现能力：

* 存储抽象能力
* 多后端统一设计

---

# 八、稳定性设计

# 8.1 幂等设计

## 问题

Worker 重试可能导致：

* 重复上传
* 重复恢复
* 数据损坏

---

## 方案

* backup_id 唯一约束
* 分布式锁
* 状态校验
* checksum 校验

---

# 8.2 超时控制

支持：

* 任务超时
* Worker 超时
* 上传超时

---

# 8.3 Retry 机制

支持：

* 指数退避
* 最大重试次数
* 死信任务

---

# 8.4 心跳机制

Worker 定期上报：

* 心跳
* 当前任务
* 资源使用情况

---

# 九、部署方案

# 9.1 Docker Compose

用于：

* 本地开发
* 单机部署
* Homelab 部署

包括：

* API
* Worker
* PostgreSQL
* Redis
* MinIO

---

# 9.2 Kubernetes 部署

支持：

* Helm Chart
* StatefulSet
* Deployment
* CronJob

体现能力：

* Kubernetes 运维经验
* 云原生交付能力

---

# 十、工程化设计

# 10.1 Monorepo

```text
devvault/
├── api/
├── worker/
├── scheduler/
├── plugins/
├── storage/
├── cli/
├── web/
├── deploy/
├── helm/
└── docs/
```

---

# 10.2 CI/CD

## GitHub Actions

包括：

* lint
* unit test
* build image
* push image
* deploy

体现能力：

* DevOps 能力
* 自动化交付能力

---

# 10.3 测试体系

## 单元测试

* plugin test
* scheduler test
* api test

## 集成测试

* backup flow
* restore flow

体现能力：

* 工程质量意识
* 稳定性保障能力

---

# 十一、项目开发阶段规划

# Phase 1（MVP）

目标：

做出真正可用版本。

功能：

* PostgreSQL Backup
* MySQL Backup
* 本地存储
* MinIO 存储
* FastAPI
* Celery Worker
* Web UI
* Docker Compose 部署

预计周期：

4~6 周

---

# Phase 2

功能：

* Docker Volume Backup
* 自动发现
* Retry 机制
* Metrics
* Grafana
* 多实例支持

预计周期：

3~4 周

---

# Phase 3

功能：

* Kubernetes Integration
* Helm
* Job 执行模式
* OpenTelemetry
* Incremental Backup
* PITR

预计周期：

4~6 周

---

# 十二、项目亮点（简历价值）

# 12.1 能体现的技术实力

## 后端系统设计

体现：

* REST API 设计
* ORM 建模
* 插件化架构
* 任务状态机

---

## 分布式系统能力

体现：

* Celery 调度体系
* Worker 并发模型
* retry/timeout/幂等
* 分布式锁

---

## 数据基础设施能力

体现：

* Backup/Restore 流程
* 对象存储链路
* 数据一致性
* PITR

---

## 云原生能力

体现：

* Docker
* Kubernetes
* Helm
* 可观测性

---

## 稳定性设计能力

体现：

* retry
* heartbeat
* metrics
* tracing
* SLA 意识

---

# 12.2 面试价值

项目可重点体现：

* 真实 ToB 系统经验迁移能力
* 从企业经验抽象通用产品能力
* Infra 平台研发能力
* Python 工程化能力
* 云原生基础设施能力

适合投递方向：

* Python 高级后端
* 数据基础设施
* DevOps Platform
* 云原生平台
* AI Infra
* 数据平台研发
* SRE 平台研发

---

# 十三、未来扩展方向

## 多节点模式

支持：

* 多 Worker
* 分布式调度
* 高可用

---

## SaaS 化

支持：

* 多租户
* 用户管理
* Billing

---

## Agent 模式

支持：

* 跨机器备份
* 远程恢复
* 边缘节点同步

---

## TUI

基于 Textual：

```bash
devvault tui
```

类似：

* lazydocker
* k9s

体现开发者工具产品能力。

---

# 十四、最终项目定位总结

DevVault 并不是一个“简历 Demo 项目”。

它的目标是：

* 一个真正可用的开发者工具
* 一个具备产品化能力的基础设施项目
* 一个能够体现高级后端与数据基础设施能力的作品

项目重点不在于功能堆砌，而在于：

* 系统设计
* 稳定性
* 工程质量
* 可扩展性
* 云原生能力
* 开发者体验

最终目标是：

让项目既能够作为个人技术作品展示，又具备真实使用价值。
