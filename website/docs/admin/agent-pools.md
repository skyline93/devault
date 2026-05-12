---
sidebar_position: 7
title: Agent 池（已下线）
description: 历史 agent_pools 模型；现由 bound_agent_id 单 Agent 绑定替代
---

# Agent 池（已下线）

**Agent 池**（**`agent_pools`**、**`agent_pool_members`**、**`policies.bound_agent_pool_id`**）与 REST **`/api/v1/agent-pools`** 已从控制面移除。策略执行绑定改为 **每条策略必填 `bound_agent_id`**；**`LeaseJobs`** 仅返回 **`policies.bound_agent_id`** 与当前 **`agent_id`** 一致的待办作业。

若需多台主机分担同一策略，可为每台主机使用独立策略（各绑定不同 **`bound_agent_id`**），或为同一租户签发 **同一 Agent 令牌** 并在多台主机 **Register** 出不同 **`agent_id`** 后分别绑定策略。

当前模型见 [Agent 舰队与版本策略](./agent-fleet.md) 与 [gRPC（Agent）](../reference/grpc-services.md) 中 **Register 与 Agent 令牌** 小节。
