---
sidebar_position: 3
title: 仓库结构
description: 主要目录职责说明
---

# 仓库结构

| 路径 | 说明 |
|------|------|
| **`src/devault/`** | API、gRPC、Agent、存储、调度等 |
| **`proto/`** | Agent `.proto` |
| **`deploy/`** | Dockerfile、Compose、Helm、Prometheus 示例 |
| **`scripts/`** | 生成与校验脚本 |
| **`tests/`** | pytest |
| **`website/`** | Docusaurus 文档站 |

生成代码通常位于 **`src/devault/grpc_gen/`**。
