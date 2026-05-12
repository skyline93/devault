## ADDED Requirements

### Requirement: IAM 登录与刷新请求不携带隐式租户头

Console 的 HTTP 客户端 **MUST NOT** 在调用外部 IAM 的 **`POST …/v1/auth/login`** 与 **`POST …/v1/auth/refresh`** 时，仅因 `localStorage` 中的当前租户缓存而自动附加 **`X-DeVault-Tenant-Id`** 或 **`X-Tenant-Id`**。租户上下文 **MUST** 在认证成功之后，由会话载荷与既有租户选择逻辑（例如 `ensureTenantSelection`）建立。

#### Scenario: 本地存在陈旧租户 ID 时 IAM 登录仍成功

- **WHEN** 浏览器 `localStorage` 中存在与即将登录用户**不兼容**的 `devault_tenant_id`（例如上一用户、已失效成员关系或任意 UUID）
- **AND** 用户提交正确的邮箱与密码调用 IAM `POST …/v1/auth/login`
- **THEN** 请求**不得**携带上述租户头（或等价地 IAM 收到的 `requested_tenant_id` 为未指定）
- **AND** 对具备至少一个活跃成员关系的非平台用户，认证成功且签发的访问令牌租户与 IAM 既有解析规则一致（例如默认成员列表中的租户）

#### Scenario: 平台管理员 IAM 登录不因残留租户失败

- **WHEN** `localStorage` 中存在任意租户 UUID
- **AND** 平台管理员用户使用 IAM `POST …/v1/auth/login`
- **THEN** 请求**不得**自动附加租户头
- **AND** 认证成功且不触发 `platform_user_tenant_disallowed`

### Requirement: 未授权时清除租户本地缓存

当 Console 全局错误处理因 **HTTP 401** 将用户重定向至登录页并清除 Bearer 凭据时，实现 **MUST** 同时从 `localStorage` 移除当前租户 ID 键（与 `STORAGE_TENANT_ID_KEY` 一致），以免后续 IAM 登录或刷新误用陈旧租户上下文。

#### Scenario: 会话过期后重新登录

- **WHEN** 访问令牌或会话失效导致 **401**
- **AND** 客户端执行登出/跳转登录页的清理逻辑
- **THEN** `STORAGE_BEARER_KEY` 与 `STORAGE_TENANT_ID_KEY` 均被移除或不再用于发往 IAM 登录/刷新的隐式租户头
