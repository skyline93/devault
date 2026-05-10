# SaaS IAM 服务详细设计方案（适用于备份平台）

你现在实际上是在设计：

```text id="y5d5h8"
企业级 SaaS 的核心基础设施
```

不是“登录模块”。

而是：

# Identity & Access Platform（IAM）

这是：

* 用户体系
* 租户体系
* 权限体系
* API 安全体系
* 审计体系

的统一核心。

如果这里设计好：

后面所有产品都能复用。

---

# 一、IAM 的职责边界（极其重要）

先明确：

# IAM 不负责业务

IAM 不应该知道：

* Backup Job
* Restore Logic
* Storage Bucket
* Agent Scheduler

这些属于业务。

---

# IAM 只负责：

```text id="zjlwm6"
1. 你是谁（Authentication）
2. 你属于谁（Tenant）
3. 你能做什么（Authorization）
4. 你做过什么（Audit）
```

---

# 二、推荐整体架构（核心）

推荐：

```text id="g7skjr"
                    ┌─────────────────┐
                    │   Frontend UI   │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   API Gateway   │
                    └────────┬────────┘
                             │
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼

 ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
 │   IAM Service  │ │ Backup Service │ │  Agent Service │
 └────────────────┘ └────────────────┘ └────────────────┘
```

---

# 三、IAM 服务内部结构

建议：

```text id="xwv1h3"
IAM Service
 ├── Auth Module
 ├── Tenant Module
 ├── RBAC Module
 ├── API Key Module
 ├── Service Account Module
 ├── Session Module
 ├── MFA Module
 ├── Audit Module
 └── Policy Module (future)
```

---

# 四、IAM 的核心数据模型

# 1. Identity Layer

---

## users

```sql id="7mu5d5"
users
------
id
email
password_hash
name
status
mfa_enabled
created_at
```

---

## sessions

```sql id="vjlwm7"
sessions
---------
id
user_id
refresh_token_hash
ip
user_agent
expires_at
created_at
```

---

# 2. Tenant Layer

---

## tenants

```sql id="w4btbj"
tenants
--------
id
name
slug
plan
status
owner_user_id
created_at
```

---

## tenant_members

```sql id="jlwm8y"
tenant_members
---------------
id
tenant_id
user_id
role_id
status
created_at
```

---

# 3. RBAC Layer

---

## roles

```sql id="jjlwm9"
roles
------
id
tenant_id nullable
name
is_system
```

---

## permissions

```sql id="jlwm0a"
permissions
------------
id
key
description
```

---

## role_permissions

```sql id="3sruvg"
role_permissions
----------------
role_id
permission_id
```

---

# 4. API Security Layer

---

## api_keys

```sql id="jlwm1b"
api_keys
---------
id
tenant_id
name
key_hash
created_by
expires_at
```

---

## api_key_scopes

```sql id="jlwm2c"
api_key_scopes
---------------
api_key_id
permission_key
```

---

# 5. Machine Identity Layer

---

## service_accounts

```sql id="jlwm3d"
service_accounts
----------------
id
tenant_id
name
role_id
token_hash
```

---

# 6. Audit Layer

---

## audit_logs

```sql id="jlwm4e"
audit_logs
-----------
id
tenant_id
actor_type
actor_id
action
resource_type
resource_id
metadata
created_at
```

---

# 五、IAM 与业务服务的关系（重点）

很多人这里会设计错。

---

# 错误做法

```text id="jlwm5f"
IAM 知道 backup.restore
IAM 知道 backup.job
IAM 知道 storage.bucket
```

这是错误耦合。

---

# 正确做法

IAM：

只知道：

```text id="jlwm6g"
permission key
```

例如：

```text id="jlwm7h"
backup.restore
backup.create
backup.read
```

但：

## 不知道 backup 长什么样。

---

# 六、真正的权限判断在哪里？

# 在业务服务

这是关键。

---

# IAM：

负责：

```text id="jlwm8i"
“用户拥有什么权限”
```

---

# Backup Service：

负责：

```text id="jlwm9j"
“这个权限是否允许操作当前资源”
```

---

# 七、完整交互流程（核心）

# 场景：

用户恢复备份。

---

## Step 1：用户登录

Frontend：

```http id="jlwm0k"
POST /auth/login
```

IAM：

返回：

```json id="jlwm1l"
{
  "access_token": "...",
  "refresh_token": "...",
  "tenant_id": "t_123"
}
```

---

# Step 2：调用 Backup API

```http id="jlwm2m"
POST /backups/restore
Authorization: Bearer xxx
```

---

# Step 3：Gateway 校验 JWT

Gateway：

验证：

* 签名
* 过期时间

然后透传：

```text id="jlwm3n"
uid
tenant_id
```

---

# Step 4：Backup Service 请求 IAM

Backup Service：

调用：

```http id="jlwm4o"
POST /authorize
```

请求：

```json id="jlwm5p"
{
  "subject": {
    "type": "user",
    "id": "u_123"
  },
  "tenant_id": "t_123",
  "action": "backup.restore"
}
```

---

# Step 5：IAM 返回

```json id="jlwm6q"
{
  "allowed": true
}
```

---

# Step 6：Backup Service 做业务校验

例如：

```text id="jlwm7r"
这个备份是否属于 tenant_id=t_123
```

然后：

真正执行 restore。

---

# 八、最重要的边界（一定记住）

# IAM 不做资源 ownership 判断

例如：

```text id="jlwm8s"
backup_789 是否属于 tenant_123
```

这是：

# Backup Service 的职责

---

# IAM 只做：

```text id="jlwm9t"
是否具备 backup.restore 权限
```

---

# 九、推荐的授权模式

推荐：

# “粗权限 + 业务细校验”

---

# IAM

做：

```text id="jlwm0u"
backup.restore
```

---

# Backup Service

做：

```text id="jlwm1v"
是否属于该 tenant
是否属于该 project
是否符合恢复策略
```

---

# 十、为什么这样设计最好

因为：

# IAM 生命周期远长于业务

业务会变：

* Backup
* Monitoring
* AI Ops

都会变。

但：

* User
* Tenant
* Permission

不会变。

---

# 十一、推荐的 Authorize API（核心）

# 统一授权接口

---

## 请求

```http id="jlwm2w"
POST /authorize
```

---

## body

```json id="jlwm3x"
{
  "subject": {
    "type": "user",
    "id": "u_123"
  },
  "tenant_id": "t_123",
  "action": "backup.restore",
  "resource": {
    "type": "backup",
    "id": "b_456"
  }
}
```

---

## 返回

```json id="jlwm4y"
{
  "allowed": true
}
```

---

# 十二、为什么 resource 要传

虽然 IAM 早期不用。

但后期：

## Resource-level Permission

就能扩展。

例如：

```text id="jlwm5z"
只能恢复某些备份
```

---

# 十三、推荐权限缓存（非常重要）

不要：

每次请求都查数据库。

---

# 推荐：

## IAM 内部：

```text id="jlwm6a"
Redis Permission Cache
```

缓存：

```text id="jlwm7b"
tenant_id:user_id -> permissions[]
```

---

# 十四、推荐权限加载方式

# 登录时加载一次

例如：

```json id="jlwm8c"
{
  "permissions": [
    "backup.read",
    "backup.restore"
  ]
}
```

---

# 然后：

Gateway：

透传：

```text id="jlwm9d"
X-Permissions
```

---

# 十五、推荐的最终架构（最佳实践）

# 推荐：

```text id="jlwm0e"
JWT
  ↓
Gateway
  ↓
Business Service
  ↓
Authorize Middleware
  ↓
IAM Permission Cache
```

---

# 十六、推荐的权限中间件

例如：

```go id="jlwm1f"
RequirePermission("backup.restore")
```

---

# Middleware：

自动：

```text id="jlwm2g"
1. 读取 JWT
2. 获取 tenant
3. 获取 permissions
4. 判断
```

---

# 十七、IAM 与 Backup Service 的真正交互

# IAM 不应该操作备份

不要：

```text id="jlwm3h"
IAM 删除 backup
```

---

# Backup Service：

才拥有：

```text id="jlwm4i"
backup domain
```

---

# IAM：

只是：

```text id="jlwm5j"
access decision service
```

---

# 十八、推荐的 Audit 设计（重要）

# 业务服务写审计

不是 IAM。

---

# 为什么

因为：

IAM 不知道：

```text id="jlwm6k"
恢复了哪个 backup
```

---

# 正确：

Backup Service：

调用：

```http id="jlwm7l"
POST /audit/log
```

---

# 内容

```json id="jlwm8m"
{
  "tenant_id": "t_123",
  "actor_id": "u_123",
  "action": "backup.restore",
  "resource_type": "backup",
  "resource_id": "b_789"
}
```

---

# 十九、推荐的服务边界（关键）

# IAM：

负责：

```text id="jlwm9n"
Identity
Tenant
Role
Permission
Session
Token
Authorize
Audit
```

---

# Backup：

负责：

```text id="jlwm0o"
Backup
Restore
Storage
Retention
Snapshot
Policy
```

---

# 二十、未来扩展能力（现在就该预留）

你现在应该预留：

---

# 1. SSO

未来：

```text id="jlwm1p"
Google
GitHub
SAML
OIDC
```

---

# 2. Policy Engine

未来：

```text id="jlwm2q"
恢复必须审批
```

---

# 3. Approval Workflow

未来：

```text id="jlwm3r"
生产恢复需要双人确认
```

---

# 4. JIT Access

未来：

```text id="jlwm4s"
临时权限
```

---

# 二十一、你现在真正应该做的

# 第一阶段（最优）

---

## 架构

```text id="jlwm5t"
单体应用
+ 独立 IAM 模块
```

---

## 逻辑隔离

不要：

```text id="jlwm6u"
一开始微服务
```

---

# 代码目录建议

```text id="jlwm7v"
/internal
  /iam
  /backup
  /agent
```

---

# 二十二、什么时候拆成真正 IAM Service

当你出现：

* 多产品
* 多团队
* 多网关
* 独立登录中心

时再拆。

---

# 二十三、最后给你一句真正关键的话

成熟 SaaS 的核心不是：

```text id="jlwm8w"
功能多
```

而是：

# “边界稳定”

尤其：

* Identity
* Tenant
* Authorization

这三个边界。

一旦设计正确：

你后面所有产品都能复用。
