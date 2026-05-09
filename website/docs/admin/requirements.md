---
sidebar_position: 4
title: 环境与依赖
description: 运行时版本与外部依赖服务
---

# 环境与依赖

## 运行时

- **Python**：`>= 3.12`（见仓库根 `pyproject.toml`）
- **容器**：演示与一体化部署推荐 Docker / Docker Compose

## 外部服务

| 服务 | 用途 |
|------|------|
| **PostgreSQL** | 元数据、任务与策略持久化 |
| **Redis** | 协调与锁（同策略备份互斥等） |
| **S3 兼容存储** | 生产路径下 Artifact 与预签名直传 |

控制面在 `DEVAULT_STORAGE_BACKEND=s3` 时为 Agent 生成预签名 URL；本地单测可使用 `local` 等非 S3 后端（见 [本地开发](../engineering/local-setup.md)）。

## Agent 侧

- 能访问控制面 **gRPC** 地址  
- 可访问同一 **S3** 端点与桶  
- 文件路径限制在 **`DEVAULT_ALLOWED_PATH_PREFIXES`**

下一步：[Docker Compose](./docker-compose.md)。
