---
sidebar_position: 1
title: 环境与依赖
description: 运行时版本与外部依赖服务
---

# 环境与依赖

## 运行时

- **Python**：`>= 3.12`（见仓库根目录 `pyproject.toml`）
- **容器**：用于演示与一体化部署时推荐 Docker / Docker Compose

## 外部服务

| 服务 | 用途 |
|------|------|
| **PostgreSQL** | 元数据、任务与策略等持久化 |
| **Redis** | 协调与缓存类用途（与实现版本一致） |
| **S3 兼容存储** | 生产路径下备份对象与预签名直传（如 MinIO、AWS S3） |

控制面在 `DEVAULT_STORAGE_BACKEND=s3` 时才会为 Agent 生成预签名 URL；本地单测插件逻辑时仍可使用 `local` 等非 S3 后端（见开发文档说明）。

## Agent 侧

- 能访问控制面 **gRPC** 地址
- 可访问同一 **S3** 端点与桶
- 文件路径限制在 `DEVAULT_ALLOWED_PATH_PREFIXES` 声明的前缀内

下一步：[Docker Compose](./docker-compose.md)。
