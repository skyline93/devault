---
sidebar_position: 2
title: gRPC（Agent）
description: Agent 侧 RPC 与源码位置
---

# gRPC（Agent）

## 接口定义

权威定义在仓库：

**`proto/agent.proto`**

修改后请在仓库根执行（需已安装 `grpcio-tools` 等开发依赖）：

```bash
bash scripts/gen_proto.sh
```

并检查生成代码中的 **相对导入**（如 `from . import agent_pb2`）是否符合当前包结构。

## 能力概述

Agent 通过 gRPC 完成注册、租约拉取、进度上报等；具体 RPC 名称与消息类型以 **`agent.proto`** 为准。

标准 **gRPC Health** 与网关场景下的端口约定见 [Agent 连接](../security/agent-connectivity.md) 与 [端口速查](./ports-and-paths.md)。
