## ADDED Requirements

### Requirement: 全局存储配置（多 profile、类型、唯一激活）

控制面 **MUST** 在元数据库中维护零条或多条 **`storage_profiles`** 记录。每条记录 **MUST** 包含 **`storage_type`**（实现至少支持 `s3`；`local` 可与现有本地存储语义对齐或按实现约束禁用多实例）。每条记录 **MUST** 携带该类型所需的非敏感连接字段（例如 S3 的 endpoint、region、bucket、use_ssl）。**MUST** 存在数据库约束或等价机制，使得在任意时刻 **至多一条** profile 的 **`is_active`** 为真；激活 profile **MUST** 用于新产生的备份写入路径在解析「当前平台对象存储」时作为权威来源。

#### Scenario: 激活切换不影响已存在制品

- **WHEN** 平台管理员将激活 profile 从 **A** 切换为 **B**
- **AND** 此前已完成的备份已在 **`artifacts`** 中记录 **`storage_profile_id = A`**
- **THEN** 对该制品的读取、预签名下载（若适用）、保留期删除 **MUST** 仍使用 profile **A** 的连接信息
- **AND** 此后新完成的备份 **MUST** 记录 **`storage_profile_id = B`**

#### Scenario: 无激活 profile 时拒绝新写入

- **WHEN** 系统中不存在 **`is_active = true`** 的 **`storage_profiles`** 行
- **AND** 控制面尝试为新作业分配对象存储写入上下文
- **THEN** 操作 **MUST** 失败并返回明确错误（HTTP 或 gRPC 语义与现有错误模式一致），**MUST NOT** 静默回退到未定义的默认桶

### Requirement: 敏感凭据加密存储

当某 **`storage_type`** 需要静态访问密钥时，控制面 **MUST** 在数据库中仅保存 **加密后的** 密钥材料；**MUST** 使用部署环境提供的根密钥（例如 **`DEVAULT_STORAGE_CONFIG_MASTER_KEY`** 或项目最终命名）进行加解密。**MUST NOT** 在 REST 响应或控制台列表中返回解密后的 **`secret_access_key`**；更新密钥 **MUST** 仅在客户端显式提交新密钥字段时覆盖密文。

#### Scenario: 列表与详情不回显明文 Secret

- **WHEN** 平台管理员调用存储配置的列表或详情 API，或打开控制台对应页面
- **THEN** 响应与 UI **MUST NOT** 包含可逆明文形式的 **`secret_access_key`**
- **AND** **MAY** 包含「已配置 / 未配置」或密钥指纹类非敏感提示

### Requirement: 制品挂载存储 profile

**`artifacts`** 表 **MUST** 包含 **`storage_profile_id`** 外键，指向写入该制品时使用的 **`storage_profiles.id`**。新写入的制品行 **MUST** 设置该列为创建时刻激活 profile 的 id（与事务内读取结果一致）。**MUST** 通过外键或等价约束防止删除仍被制品引用的 profile（除非实现显式级联策略且规格另行规定）。

#### Scenario: 历史制品迁移后外键有效

- **WHEN** 数据库迁移为既有 **`artifacts`** 行写入默认 **`storage_profile_id`**
- **THEN** 该 id **MUST** 引用迁移脚本插入的种子 **`storage_profiles`** 行
- **AND** 迁移完成后 **`storage_profile_id`** 对新生据 **MUST** 为非空且满足外键

### Requirement: 下线租户 BYOB（租户不得覆盖存储）

控制面 **MUST NOT** 接受或持久化租户级别的对象存储覆盖：租户实体及相关 API **MUST** 移除 **`s3_bucket`**、**`s3_assume_role_arn`**、**`s3_assume_role_external_id`** 字段。存储客户端与桶解析 **MUST** 仅依据 **`storage_profiles`**（及制品上挂载的 id），**MUST NOT** 再实现「租户优先于全局」的 AssumeRole 或桶名覆盖逻辑。

#### Scenario: 租户 PATCH 不再包含存储字段

- **WHEN** 调用方对 **`PATCH /api/v1/tenants/{id}`** 提交此前用于 BYOB 的 JSON 字段
- **THEN** 服务端 **MUST** 忽略或拒绝这些字段（实现选择其一并在 OpenAPI 中移除其声明）
- **AND** 数据库 **MUST NOT** 再存在对应租户列

### Requirement: 平台管理员专用 REST 与控制台

存储配置的创建、读取、更新、删除及「设为激活」**MUST** 仅允许 **`AuthContext.principal_kind == platform`** 且满足现有平台管理员角色约束（与 **`require_admin`** 语义一致）。控制台 **MUST** 将存储管理菜单与路由限制为 **`GET /api/v1/auth/session`** 返回的 **`principal_kind === 'platform'`** 的会话（并与 MFA / 强制改密门禁组合）；租户管理员会话 **MUST NOT** 能访问该页面或成功调用上述 API。

#### Scenario: 租户管理员收到 403

- **WHEN** 持有租户用户 JWT（**`principal_kind` 为 `tenant_user`**）且 **`role` 为 `admin`** 的调用方请求存储管理写接口
- **THEN** 服务端 **MUST** 返回 **403**，**MUST NOT** 修改任何 **`storage_profiles`** 行

### Requirement: 部署环境根密钥

用于加解密 **`storage_profiles`** 中敏感字段的根密钥 **MUST** 仅由部署环境（密钥管理器、Kubernetes Secret、Compose secret 等）注入，**MUST NOT** 由应用首次启动自动生成并仅存在于库内。缺少该环境变量而存在需解密的 profile 时，应用 **MUST** 在启动或首次解密时失败并记录清晰日志。

#### Scenario: 缺少主密钥时拒绝解密

- **WHEN** 数据库中存在含密文凭据的 profile
- **AND** 进程环境中未配置根加密密钥
- **THEN** 控制面 **MUST NOT** 以明文占位符替代凭据继续访问对象存储
