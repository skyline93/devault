---
slug: /
sidebar_position: 0
title: 文档首页
description: DeVault 文档导航 — 按角色进入相应章节
---

# DeVault 文档

DeVault 是面向企业与团队的 **备份与恢复 SaaS 平台**：多租户控制面提供 HTTP API、OpenAPI、gRPC 与 Web 控制台；边缘 **Agent** 以 **Pull** 模型拉取作业，经 **预签名 URL** 与 **S3 兼容对象存储**直传数据面，控制面不承载备份字节流。

请按你的角色选择入口：

| 角色 | 说明 | 入口 |
|------|------|------|
| **决策与架构** | 产品价值、部署形态、一页纸架构与路线图 | [产品概览](./product/overview.md) |
| **终端用户** | 概念、快速体验、备份/恢复与控制台操作 | [使用手册](./user/index.md) |
| **管理员 / 运维** | 租户与权限、部署、观测、存储与 Agent 运维 | [平台运维](./admin/index.md) |
| **安全与合规** | 信任边界、TLS、访问控制、加密与白皮书摘要 | [信任中心](./trust/index.md) |
| **集成开发** | HTTP/gRPC、端口与环境变量速查 | [API 与参考](./reference/http-api.md) |
| **工程与贡献** | 本地开发、仓库结构、平台实现架构、发版与契约 | [工程指南](./engineering/index.md) |

全站产品界面统称 **Web 控制台**（URL 前缀 **`/ui/*`**）；HTTP API 统称 **REST**（见 OpenAPI）。

详细功能与边界以当前发行版代码及 [变更记录](https://gitee.com/greene93/devault/blob/dev/CHANGELOG.md) 为准。
