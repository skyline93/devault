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

## Compose（Envoy 在主文件；Agent TLS 为薄叠加）

**`grpc-gateway`** 已在 **`deploy/docker-compose.yml`** 中，启用 profile **`with-grpc-tls`**。栈内 Agent 改走 TLS 时，再叠加 **`deploy/compose.include/grpc-tls-agent.yml`**（或薄包装 **`deploy/docker-compose.grpc-tls.yml`**，其内 `include` 该片段），仅覆盖 **agent** 的 `DEVAULT_GRPC_*` 与 CA 挂载。

```bash
docker compose -f deploy/docker-compose.yml -f deploy/docker-compose.grpc-tls.yml \
  --profile with-control-plane --profile with-agent --profile with-grpc-tls pull
docker compose -f deploy/docker-compose.yml -f deploy/docker-compose.grpc-tls.yml \
  --profile with-control-plane --profile with-agent --profile with-grpc-tls up -d
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
