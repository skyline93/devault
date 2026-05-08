---
sidebar_position: 4
title: 配置参考
description: 常用环境变量分组说明
---

# 配置参考

以下为常用变量分组，完整列表以代码内 `pydantic-settings` 定义及 `deploy/docker-compose.yml` 为准。

## 控制面 / API

| 变量 | 说明 |
|------|------|
| `DEVAULT_DATABASE_URL` | SQLAlchemy 数据库 URL（如 `postgresql+psycopg://...`） |
| `DEVAULT_REDIS_URL` | Redis 连接串 |
| `DEVAULT_API_TOKEN` | HTTP Bearer 与简易 UI Basic 密码 |
| `DEVAULT_GRPC_LISTEN` | 绑定 gRPC 的 `host:port`（如 `0.0.0.0:50051`） |
| `DEVAULT_ENV_NAME` | 环境名标签（指标等） |

## 存储后端（S3）

| 变量 | 说明 |
|------|------|
| `DEVAULT_STORAGE_BACKEND` | 设为 `s3` 以启用预签名与 Agent 直传路径 |
| `DEVAULT_S3_ENDPOINT` | S3 API 端点 |
| `DEVAULT_S3_ACCESS_KEY` / `DEVAULT_S3_SECRET_KEY` | 访问密钥 |
| `DEVAULT_S3_BUCKET` | 桶名（须事先存在） |
| `DEVAULT_S3_USE_SSL` | 是否使用 HTTPS |
| `DEVAULT_S3_REGION` | 部分云厂商需要 |

大对象相关阈值见 [存储调优](../storage/tuning.md)。

## Agent

| 变量 | 说明 |
|------|------|
| `DEVAULT_GRPC_TARGET` | 控制面 gRPC 地址（如 `api:50051`） |
| `DEVAULT_ALLOWED_PATH_PREFIXES` | 逗号分隔路径前缀，如 `/data,/restore` |
| `DEVAULT_API_TOKEN` | 与注册/鉴权相关的令牌（与实现版本一致） |
| `DEVAULT_AGENT_MULTIPART_STATE_DIR` | （可选）Multipart 续传状态与 WIP `bundle.tar.gz` 的根目录；默认 `~/.cache/devault-agent` |

## 与 Compose 对齐

演示环境默认值见 `deploy/docker-compose.yml`（如 `changeme` Token、MinIO 凭证等）。**生产环境务必替换**。
