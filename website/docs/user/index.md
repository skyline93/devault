---
sidebar_position: 1
title: 使用手册导读
description: 终端用户文档路径与适用范围
---

# 使用手册导读

## 适用范围

在 **单个租户作用域内** 使用 API、CLI 或 **Web 控制台**完成备份、恢复、策略与调度。租户解析规则（`X-DeVault-Tenant-Id` 与默认 slug）见 [租户与访问控制](../admin/tenants-and-rbac.md)。

若你负责装机与集群运维，请参阅 [平台运维](../admin/index.md)。

---

## 按任务选读（三条路径）

### 路径 A：首次理解产品

1. [核心概念](./concepts.md)  
2. [架构一页纸](../product/architecture.md)（可选，弄清控制面 / Agent / 存储分工）

### 路径 B：最短跑通闭环（自建栈）

1. [快速开始](./quickstart.md)（Docker Compose + `curl`）  
2. [备份与恢复流程](./backup-and-restore.md)

### 路径 C：日常配置与合规相关操作

1. [策略与定时](./policies-and-schedules.md)、[保留与生命周期](./retention-lifecycle.md)  
2. [恢复演练](./restore-drill.md)、[Web 控制台](./web-console.md)

REST 路径与调试界面见 [HTTP API 参考](../reference/http-api.md)。
