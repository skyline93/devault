# console-session Specification

## Purpose
TBD - created by archiving change fix-console-login-tenant-context. Update Purpose after archive.
## Requirements
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

### Requirement: IAM 首次登录强制改密门禁

当控制台使用 IAM 模式完成 `POST …/v1/auth/login`（含 MFA 第二步完成后的等价成功路径）且响应体中 **`must_change_password`** 为 **true** 时，控制台 **MUST** 在用户访问任何需会话的业务路由之前，将其引导至 **IAM 改密**流程；**MUST NOT** 在该状态下将用户直接导航至工作台或平台管理等业务首页，就好像已完成正常登录一样。

#### Scenario: 须改密用户登录后被引导至改密页

- **WHEN** IAM `POST …/v1/auth/login` 成功返回 `access_token`
- **AND** 响应体中 `must_change_password` 为 `true`
- **THEN** 客户端持久化访问令牌（与现有 Bearer 存储策略一致）
- **AND** 用户被导航至控制台提供的 **改密页面**（例如 `/user/change-password`）
- **AND** 全局 `initialState` / `access` 将写能力与平台管理能力关闭，直至改密成功（语义上与 `needs_mfa` 门禁一致）

#### Scenario: 改密成功后进入正常控制台会话

- **WHEN** 用户在改密页提交有效「当前密码 / 新密码」并调用 IAM `POST …/v1/auth/change-password` 成功
- **THEN** IAM 侧 `must_change_password` 标志被清除（与 IAM 现有语义一致）
- **AND** 客户端使用刷新后的凭据拉取控制面 `GET /api/v1/auth/session`（或等价流程）并进入与现有一致的登录后导航（含 `redirect` 查询参数的安全校验）

### Requirement: IAM 自主改密页面

控制台 **MUST** 提供不依赖业务布局壳的独立页面，供已持有 IAM Bearer 的用户调用 **`POST …/v1/auth/change-password`** 完成密码更新；该页面 **MUST** 在令牌缺失时重定向至登录页。

#### Scenario: 未登录访问改密页

- **WHEN** 用户未持有有效 IAM Bearer 凭据而直接打开改密页 URL
- **THEN** 客户端重定向至 `/user/login`（或项目约定的登录入口）

