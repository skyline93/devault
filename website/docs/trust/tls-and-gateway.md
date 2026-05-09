---
sidebar_position: 4
title: TLS 与网关
description: gRPC TLS、mTLS 与 Envoy 示例路径
---

# TLS 与网关

## 开发证书

```bash
bash scripts/gen_grpc_dev_tls.sh
```

## Compose 叠加

```bash
docker compose -f deploy/docker-compose.yml -f deploy/docker-compose.grpc-tls.yml up --build
```

典型：**Agent → 网关 TLS**，网关 → **`api:50051` 明文 gRPC**。

## Envoy 边缘限流

**`deploy/envoy/envoy-grpc-tls.yaml`** 中 **`local_rate_limit`**（约 40 令牌/秒、桶 80）与控制面进程内 **`DEVAULT_GRPC_RPS_PER_PEER`** 形成双层限流。

多 **api** 副本、**ROUND_ROBIN** 见 [gRPC 与 API 多实例](../admin/grpc-multi-instance.md)。

## mTLS 与审计

按部署在网关或后端启用 mTLS、连接审计。以当前分支 `deploy` 与代码为准。

## 操作检查清单

- [ ] 证书 SAN 与 Agent 主机名一致
- [ ] 网关上游指向正确 gRPC 地址
- [ ] 仅开放必要端口；凭证不入 Agent 镜像
