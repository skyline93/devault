---
sidebar_position: 5
title: 可观测性
description: Prometheus、健康检查与日志
---

# 可观测性

## Prometheus

控制面暴露 **`GET /metrics`**（Prometheus 文本格式）。`deploy/docker-compose.yml` 中包含 **prometheus** 服务示例，将抓取目标指向 API。

常用排查步骤：

1. 确认 `api` 健康检查已通过
2. 浏览器或 `curl` 访问 `http://<host>:8000/metrics`
3. 在 Prometheus UI 中查询相关指标

## 健康检查

HTTP 层提供用于编排的就绪类端点（如 Compose 中使用的 **`/healthz`**）。部署时应将负载均衡/滚动更新与此类端点绑定。

## 版本信息

**`GET /version`** 返回 JSON 版本信息，便于与镜像标签或 Git SHA 对齐。

## 日志

- 容器标准输出：由运行时收集（如 `docker compose logs -f api`）
- 生产建议接入集中日志（与基础设施一致）

## gRPC Health

Agent 侧依赖标准 gRPC Health 语义时，请参考 `proto` 与实现中的 health 服务注册方式（与 [gRPC 服务参考](../reference/grpc-services.md) 交叉阅读）。
