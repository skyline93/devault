---
sidebar_position: 2
title: 仓库结构
description: 主要目录职责说明
---

# 仓库结构

| 路径 | 说明 |
|------|------|
| **`src/devault/`** | Python 包：API、gRPC、Agent、存储、调度等 |
| **`proto/`** | Agent gRPC 的 `.proto` 定义 |
| **`deploy/`** | Dockerfile、Compose、Prometheus 示例等 |
| **`scripts/`** | 代码生成与健康检查类脚本 |
| **`tests/`** | pytest 用例 |
| **`website/`** | 本 Docusaurus 文档站 |

生成代码通常位于 `src/devault/grpc_gen/`（以 `.gitignore` 与脚本约定为准）。
