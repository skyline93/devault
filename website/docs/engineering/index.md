---
sidebar_position: 1
title: 工程指南导读
description: 研发与贡献者文档路径
---

# 工程指南导读

## 适用范围

内核开发、契约维护、版本发布与 CI 校验。产品与售前可用的**简短架构鸟瞰**见 [架构一页纸](../product/architecture.md)；RPC 序列与实现对齐见本目录 [平台实现架构](./platform-architecture.md)，避免两篇重复抄写同一张大图。

终端用户文档见 [使用手册](../user/index.md)；对外 API 见 [参考](../reference/http-api.md)。

---

## 按任务选读

| 任务 | 文档 |
|------|------|
| **搭本地环境、跑 API/Agent** | [本地开发](./local-setup.md)、[仓库结构](./project-structure.md) |
| **理解 Pull、控制面/数据面实现对照** | [平台实现架构](./platform-architecture.md) |
| **控制面 Postgres 表与 ER** | [控制面数据库 ER 图](./control-plane-database-er.md) |
| **改 proto、发版、兼容矩阵** | [兼容性与版本矩阵](./compatibility.md)、[发版与变更记录](./releasing.md) |
| **测试与 CI** | [测试](./testing.md) |

权威版本号与 `compatibility.json` 约定见 [发版与变更记录](./releasing.md) 及仓库根 `docs/RELEASE.md`。
