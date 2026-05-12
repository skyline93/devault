## ADDED Requirements

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
