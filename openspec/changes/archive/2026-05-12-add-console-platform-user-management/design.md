## Context

- **IAM**：`POST /v1/platform/users` 创建普通用户，请求体含 `password`（策略最小长度）、`must_change_password`；`POST /v1/tenants/{tenant_id}/members` 以邮箱绑定已存在用户到租户角色（`tenant_admin` | `operator` | `auditor`）。平台管理员 JWT（`is_platform_admin` + `devault.platform.admin`）在 `ensure_tenant_scope` 下可对任意租户调用成员 API。
- **控制面**：`GET /api/v1/tenants` 供平台管理员选择租户（与现有 `TenantSwitcher` 数据源一致）。
- **控制台**：IAM 模式登录已解析 `TokenOut` 类型但未消费 `must_change_password`；无 `/user/change-password` 页。

## Goals

- 平台管理员在 **仅控制台** 完成：选租户 → 填邮箱/显示名/角色 → 生成并展示一次性初始密码 → 创建用户并写入租户成员。
- 新用户使用初始密码登录后，**必须先改密** 才能使用控制台业务功能（与 MFA 门禁模式类似，独立分支）。
- **不**引入邮件邀请依赖；不破坏现有 IAM 登录「不在 login/refresh 上误带租户头」等已规格化行为（见 `openspec/specs/console-session/spec.md`）。

## Non-Goals

- 不要求在本变更内实现「全平台用户目录」跨租户聚合列表（IAM 当前无 `GET /v1/platform/users`）；管理页以 **按租户成员列表** 为基线。
- 不要求修改 IAM 密码策略或成员模型的语义（除非实现阻塞时再开子任务）。

## Decisions

1. **初始密码来源**：由 **控制台生成** 符合 IAM 策略的随机密码并随 `POST /v1/platform/users` 提交；创建响应 **不**回传密码。展示仅在创建成功后的 UI 一次性 Modal/Alert（可复制）。  
   - *备选（未采纳为范围）*：扩展 IAM 由服务端生成并仅在 201 响应返回一次——需后端改动，放入 Future。
2. **创建顺序**：严格 **先** `POST /v1/platform/users`（`must_change_password: true`），**再** `POST /v1/tenants/{id}/members`，避免 `user_not_found`。
3. **改密门禁**：IAM 登录成功后若 `must_change_password === true`，写入 Bearer 后跳转 **`/user/change-password`**（layout: false 与登录页同级）；改密成功后刷新令牌或重新拉会话，再进入 `/overview/welcome` 或 `redirect` 参数。`getInitialState` / 会话守卫应对该标志做与 `needs_mfa` 类似的写能力关闭（具体字段名在实现中选 `initialState` 扩展或复用模式）。
4. **IAM 请求路径**：沿用现有 `IAM_API_PREFIX`（如 `/iam-api`）与控制台 `request` 拦截器约定；平台页仅在 `canAdmin` 下可见。

## Risks / Trade-offs

- **密钥展示**：运维需安全渠道分发初始密码；UI 须提示勿通过不安全渠道传播。  
- **部分失败**：用户已创建但加成员失败时需明确错误与重试/人工补救（任务清单含幂等与提示）。  
- **刷新 deep-link**：用户 bookmark 业务页时在「须改密」状态下应被重定向到改密页（与 MFA 一致思路）。

## Open Questions

- 成员 **PATCH/DELETE** 是否在本变更一并暴露 UI，或仅列表 + 创建；默认 **列表 + 创建** 为 MVP，其余跟随后续 PR。
