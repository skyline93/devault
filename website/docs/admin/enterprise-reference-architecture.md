---
sidebar_position: 11
title: 企业参考架构
description: DMZ、网关、控制面 VPC 与出站策略单页图
---

# 企业参考架构

**生产常见拆分**单页视图，便于安全评审。原则与控制/数据面见 [架构一页纸](../product/architecture.md) 与 [平台实现架构](../engineering/platform-architecture.md)；Helm 安装见 [Kubernetes（Helm）](./kubernetes-helm.md)。

## 网络分区与信任域

```mermaid
flowchart LR
  subgraph corp["客户内网"]
    SRC[受保护数据源]
    AG[DeVault Agent]
    SRC --> AG
  end

  subgraph dmz["DMZ / 专线对端区"]
    GW[gRPC 网关<br/>TLS · 限流 · 审计]
  end

  subgraph vpc["控制面 VPC"]
    API[HTTP API / UI / OpenAPI]
    GRPC[gRPC Agent 服务]
    PG[(PostgreSQL)]
    RD[(Redis)]
    SCH[devault-scheduler]
    API --> PG
    GRPC --> PG
    SCH --> PG
    GRPC --> RD
    SCH --> RD
  end

  subgraph obj["对象存储区域"]
    S3[(S3 兼容桶<br/>预签名 / STS)]
  end

  AG -->|"443 出站 gRPC"| GW
  GW --> GRPC
  AG -->|"443 出站 HTTPS 数据面"| S3
  GRPC -->|"控制面凭证与校验"| S3
  API -->|"运维/集成"| PG
```

| 边界 | 说明 |
|------|------|
| **Agent → 网关** | 出站 TLS gRPC（Pull）；不暴露 Postgres/Redis 到客户侧 |
| **Agent → 对象存储** | 备份/恢复字节流；短时预签名 |
| **控制面 → 对象存储** | Manifest、Multipart 收尾、保留删除；可用 AssumeRole |

HTTP API：生产建议 TLS、OIDC/API Key/RBAC（见 [租户与访问控制](./tenants-and-rbac.md)）。

## 出站与防火墙

- **Agent**：网关 `443`、对象存储 `443`。
- **控制面**：Postgres、Redis、S3、（可选）STS；**无需**入连客户内网。

## 相关文档

- [TLS 与网关](../trust/tls-and-gateway.md)
- [gRPC 与 API 多实例](./grpc-multi-instance.md)
- [安全白皮书摘要](../trust/whitepaper.md)
