
# 企业级 SaaS 备份平台组织与 IAM 体系设计方案

# 1. 文档目标

本文档用于定义：

- 企业级 SaaS 备份平台的组织模型
- IAM（Identity & Access Management）体系
- 用户注册登录流程
- Tenant（租户）生命周期
- 权限模型
- 平台管理员模型
- 业务服务与 IAM 的交互边界

目标：

1. 支持企业级多租户
2. 支持后续平台化扩展
3. 支持多个业务系统复用 IAM
4. 支持企业安全能力扩展
5. 避免早期设计导致后期重构

---

# 2. 核心设计原则

## 2.1 Platform ≠ Tenant

系统必须区分：

| 概念 | 含义 |
|---|---|
| Platform | 整个 SaaS 平台 |
| Tenant | 客户组织/工作空间 |
| User | 用户身份 |
| Membership | 用户在某组织中的角色 |

关系：

```text
Platform
 └── Tenants
       └── Users
````

---

## 2.2 用户不是租户

错误模型：

```text
User -> Tenant
```

正确模型：

```text
User <-> Membership <-> Tenant
```

原因：

* 一个用户可能属于多个组织
* MSP/代理商/顾问场景常见
* 企业协作必须支持

---

## 2.3 权限属于租户上下文

同一个用户：

| Tenant    | Role     |
| --------- | -------- |
| Company A | admin    |
| Company B | readonly |

因此：

```text
权限 = 用户在某租户中的身份
```

---

## 2.4 IAM 与业务解耦

IAM 不负责：

* Backup
* Restore
* Storage
* Job

IAM 只负责：

```text
Authentication
Authorization
Tenant Context
Audit
```

---

# 3. 系统整体架构

```text
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

# 4. IAM 服务职责

IAM 负责：

```text
Identity
Tenant
Membership
RBAC
Session
JWT
API Key
Service Account
Authorize
Audit
```

业务服务负责：

```text
Backup
Restore
Storage
Agent
Policy
Scheduler
```

---

# 5. 组织模型

# 5.1 Platform（平台层）

表示：

```text
整个 SaaS 平台
```

由平台运营方管理。

例如：

* 平台运维
* 系统监控
* Tenant 管理
* 套餐管理

---

# 5.2 Tenant（租户层）

表示：

```text
客户组织
```

例如：

* 腾讯
* 字节
* 某创业公司

每个 Tenant：

* 数据独立
* 权限独立
* 配置独立

---

# 5.3 User（用户身份）

表示：

```text
一个全局身份
```

User 不直接属于 Tenant。

---

# 5.4 Membership（组织关系）

表示：

```text
用户在某 Tenant 中的角色
```

例如：

| User  | Tenant    | Role     |
| ----- | --------- | -------- |
| Alice | Company A | admin    |
| Alice | Company B | readonly |

---

# 6. 平台初始化流程

# 6.1 系统首次部署

系统启动后：

```text
Platform 存在
Platform Admin 存在
Tenant 不存在
```

---

# 6.2 Bootstrap Platform Admin

通过环境变量初始化：

```env
BOOTSTRAP_ADMIN_EMAIL=admin@yourapp.com
BOOTSTRAP_ADMIN_PASSWORD=xxxx
```

系统首次启动时：

自动创建：

```text
platform_admin
```

---

# 6.3 Platform Admin 特点

Platform Admin：

* 不属于任何 Tenant
* 不走 tenant_members
* 属于 platform scope

用于：

* Tenant 管理
* 系统维护
* 平台运营

---

# 7. 注册与组织创建流程

系统支持两种模式：

---

# 7.1 自助注册（Self-Serve）

适用于：

* 官网试用
* 自助 SaaS

流程：

```text
用户注册
  ↓
创建 User
  ↓
创建 Tenant
  ↓
创建 Membership(owner)
  ↓
登录系统
```

结果：

```text
注册用户自动成为 Tenant Owner
```

---

# 7.2 邀请注册（Enterprise）

适用于：

* 企业协作
* 团队成员加入

流程：

```text
Admin Invite User
  ↓
生成 invite token
  ↓
用户打开邀请链接
  ↓
创建 User（如不存在）
  ↓
加入已有 Tenant
```

注意：

```text
邀请注册不会创建 Tenant
```

---

# 8. 登录流程

# 8.1 登录入口

推荐：

```text
统一登录入口
```

例如：

```text
/login
```

Platform Admin 与 Tenant User 使用同一入口。

---

# 8.2 登录流程

```text
输入邮箱密码
  ↓
验证身份
  ↓
查询所属 tenants
  ↓
选择 active tenant
  ↓
签发 JWT
```

---

# 8.3 JWT 内容

```json
{
  "uid": "u_123",
  "tid": "t_456",
  "role": "admin",
  "session_id": "s_789"
}
```

---

# 8.4 登录后跳转

根据 scope：

---

## Platform Admin

进入：

```text
/platform
```

---

## Tenant User

进入：

```text
/app
```

---

# 9. Tenant 生命周期

# 9.1 创建 Tenant

创建方式：

| 方式   | 创建者            |
| ---- | -------------- |
| 自助注册 | 用户             |
| 平台创建 | Platform Admin |

---

# 9.2 删除 Tenant

仅：

```text
Tenant Owner
```

或：

```text
Platform Admin
```

可执行。

---

# 9.3 Tenant Ownership

默认：

```text
创建 Tenant 的用户
```

自动成为：

```text
owner
```

---

# 10. RBAC 权限模型

# 10.1 模型

```text
User
 -> Membership
   -> Role
      -> Permissions
```

---

# 10.2 系统角色

## owner

最高组织权限。

可：

* 删除 Tenant
* 管理 Billing
* 配置 SSO
* 转移 Ownership

---

## admin

组织管理员。

可：

* 管理成员
* 创建 API Key
* 管理 Backup

不可：

* 删除 Tenant
* 管理 Billing

---

## operator

运维角色。

可：

* Backup
* Restore
* 查看任务

---

## readonly

只读角色。

---

# 10.3 Permission 命名

规范：

```text
resource.action
```

例如：

```text
backup.create
backup.read
backup.restore
backup.delete

apikey.create
apikey.delete

user.invite
user.remove
```

---

# 11. 授权流程

# 11.1 IAM 负责什么

IAM 负责：

```text
用户是否拥有某权限
```

例如：

```text
backup.restore
```

---

# 11.2 Backup Service 负责什么

Backup Service 负责：

```text
资源是否允许被当前 tenant 操作
```

例如：

```text
backup_123 是否属于 tenant_456
```

---

# 11.3 完整授权流程

```text
用户请求 Restore
  ↓
Gateway 验证 JWT
  ↓
Backup Service 调用 IAM Authorize
  ↓
IAM 返回 allow/deny
  ↓
Backup Service 校验资源归属
  ↓
执行恢复
```

---

# 12. API Key 模型

# 12.1 原则

API Key：

```text
不继承用户全部权限
```

---

# 12.2 API Key Scope

每个 API Key 拥有独立 scopes。

例如：

```text
backup.read
backup.create
```

---

# 12.3 API 调用流程

```text
API Key
  ↓
验证 hash
  ↓
加载 scopes
  ↓
权限判断
```

---

# 13. Service Account 模型

用于：

* Agent
* Scheduler
* 自动任务

原则：

```text
机器身份 ≠ 用户身份
```

---

# 14. 审计日志

# 14.1 原则

业务服务负责写审计。

不是 IAM。

---

# 14.2 审计内容

```text
谁
在什么时间
对什么资源
执行了什么操作
```

---

# 14.3 高危操作必须审计

例如：

* Restore
* Delete Backup
* Export Data
* Rotate Credential

---

# 15. 多租户隔离

# 15.1 推荐方案

```text
Shared DB + tenant_id
```

---

# 15.2 所有业务表必须包含

```sql
tenant_id
```

---

# 15.3 所有查询必须自动注入

```sql
WHERE tenant_id = ?
```

---

# 16. 推荐阶段性演进

# Phase 1（MVP）

必须：

* User
* Tenant
* Membership
* RBAC
* JWT
* API Key
* Service Account
* Audit Log

---

# Phase 2（企业增强）

增加：

* SSO/SAML
* SCIM
* 自定义角色
* Resource-level Permission
* IP Allowlist

---

# Phase 3（平台化）

增加：

* MSP
* Organization Tree
* Approval Workflow
* Policy Engine
* JIT Access

---

# 17. 推荐目录结构（单体阶段）

```text
/internal
  /iam
  /backup
  /agent
```

建议：

```text
逻辑模块化
而不是立即微服务化
```

---

# 18. 推荐最终架构

```text
Identity Layer
 ├── User
 ├── Session
 ├── MFA
 └── SSO

Organization Layer
 ├── Tenant
 ├── Membership
 └── Invitation

Access Layer
 ├── Role
 ├── Permission
 ├── API Key
 └── Service Account

Security Layer
 ├── Audit
 ├── Approval
 ├── IP Restriction
 └── Policy Engine

Business Layer
 ├── Backup
 ├── Restore
 ├── Storage
 └── Agent
```

---

# 19. 最终设计原则总结

必须牢记：

---

## Platform ≠ Tenant

---

## User ≠ Membership

---

## 登录 ≠ 授权

---

## IAM 不负责业务资源

---

## 权限属于租户上下文

---

## API Key 必须有独立 Scope

---

## Restore 属于高危权限

---

## 审计日志必须完整

---

## 多租户隔离优先级高于功能

---

# 20. 最终目标

最终形成：

```text
统一 IAM 平台
+
多个业务平台复用
```

包括：

* Backup Platform
* Monitoring Platform
* DevOps Platform
* AI Ops Platform
* Internal Tools

```
```
