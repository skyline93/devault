---
sidebar_position: 2
title: TLS 与网关
description: gRPC TLS、mTLS 与 Envoy 示例路径
---

# TLS 与网关

## 开发证书

仓库提供脚本用于生成本地开发 TLS 材料（路径与用法以脚本内注释为准），例如：

```bash
bash scripts/gen_grpc_dev_tls.sh
```

## Compose 叠加

在 `deploy` 目录下，可在基础 `docker-compose.yml` 上叠加 gRPC TLS 相关文件，例如：

```bash
docker compose -f deploy/docker-compose.yml -f deploy/docker-compose.grpc-tls.yml up --build
```

典型模式：**Agent 连接网关 TLS 端口**，网关将请求转发到内网 **`api:50051` 明文 gRPC**。

扩展多个 **`api` 副本**、Envoy **ROUND_ROBIN** 与 Compose 端口注意事项见 [gRPC 与 API 多实例部署](../install/grpc-multi-instance.md)。

## mTLS 与审计

根据部署目标，可在网关或控制面侧启用 mTLS、连接审计与限流。实现细节随版本演进，请以当前分支下的 `deploy` 与相关文档代码为准。

## 操作检查清单

- [ ] 证书 SAN 与 Agent 使用的主机名一致
- [ ] 网关上游指向正确的 `api` gRPC 地址
- [ ] 仅开放必要端口；对象存储凭证不落盘在 Agent 镜像内
