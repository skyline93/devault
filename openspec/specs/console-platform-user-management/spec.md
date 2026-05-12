# console-platform-user-management Specification

## Purpose
TBD - created by archiving change add-console-platform-user-management. Update Purpose after archive.
## Requirements
### Requirement: 平台管理员在控制台创建用户并绑定租户成员

具备 **`canAdmin`** 的平台控制台主体 **MUST** 能够通过控制台 UI 在单一流程中：（1）在 IAM 创建普通用户并设置 **`must_change_password: true`**；（2）将该用户以选定角色加入 **指定租户** 的成员关系。该流程 **MUST NOT** 依赖控制面邮件邀请 API。

#### Scenario: 创建成功并展示一次性初始密码

- **WHEN** 平台管理员在「创建用户」页提交有效表单（含租户、邮箱、显示名、成员角色）
- **THEN** 控制台生成符合 IAM 密码策略的初始密码并调用 IAM `POST /v1/platform/users` 成功
- **AND** 随后使用同一邮箱调用 IAM `POST /v1/tenants/{tenant_id}/members` 成功
- **AND** 界面以一次性、可复制的方式向操作者展示初始密码，并附带安全提示（例如勿通过不安全渠道传播）

#### Scenario: 成员绑定失败时的可理解反馈

- **WHEN** IAM 用户创建成功但 `POST /v1/tenants/{tenant_id}/members` 失败
- **THEN** 界面展示明确错误信息，并提示可能的人工补救步骤（例如通过平台工具修正成员关系或重试），**MUST NOT** 假装两步均已成功

### Requirement: 平台管理员按租户查看成员列表

具备 **`canAdmin`** 的平台控制台主体 **MUST** 能够在控制台 UI 中选定租户并查看该租户在 IAM 下的成员列表（字段至少覆盖 IAM `MemberOut` 所暴露的身份与角色信息）。

#### Scenario: 选择租户后加载成员表

- **WHEN** 平台管理员在「用户/成员管理」页选择某一租户
- **THEN** 控制台调用 IAM `GET /v1/tenants/{tenant_id}/members` 并渲染表格（或等价列表组件）
- **AND** 若请求失败，展示可读错误且不伪造空列表为成功状态

### Requirement: 平台用户管理入口位于平台管理菜单下

上述创建与列表能力 **MUST** 作为 **平台管理**（`/platform`）下的子菜单项暴露，且 **MUST** 与现有「组织/租户」管理能力并列可见（在 `canAdmin` 为真时）。

#### Scenario: 平台管理员侧栏可见新菜单

- **WHEN** 当前用户 `canAdmin` 为 `true`
- **THEN** 侧栏「平台管理」分组下出现指向「创建用户」与「用户/成员管理」的菜单项（具体文案以实现与 i18n 为准）

