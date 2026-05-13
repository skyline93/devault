## Context

控制面已具备 `local` / `s3` 存储抽象、S3 预签名与 multipart、gRPC 数据面、scheduler 保留清理；租户表含 BYOB 字段并由 `build_s3_client_for_tenant` / `effective_s3_bucket` 解析。会话与权限上，HTTP **`require_admin`** 已限制为 **`principal_kind == platform`**，但控制台 `/platform` 菜单仍可能仅依赖 `role === admin'`，需在存储功能上显式对齐「仅平台主体」。

## Goals / Non-Goals

**Goals:**

- 多条全局 **`storage_profiles`**，字段含 **`storage_type`**、连接参数、可选加密静态凭证；**同一时间仅一条激活**。
- 根加密密钥仅来自**部署环境**；库内仅存密文。
- **`artifacts.storage_profile_id`** 新数据写入时必填；历史行可为 **NULL**，读/保留清理对 **NULL** 回退到当前激活 profile（单存储时代兼容）。
- **完全移除**租户级存储覆盖（BYOB）及相关 API/UI/文档。
- 控制台提供存储 **CRUD + 激活**，且仅平台管理员会话可用；控制面 REST 与之一致。
- 提供可重复的 **迁移**：建表、**可空** `artifacts.storage_profile_id` 与外键、删租户列；**不**插入默认 profile。

**Non-Goals:**

- 在本变更中实现非 S3 协议的新存储驱动（`storage_type` 可预留枚举，`local` 与现网行为对齐策略在任务中明确即可）。
- 将数据库连接串或 IAM JWT 验证根信任迁入本功能（仍属既有部署职责）。
- 自动搬迁已有对象到新桶（对象数据迁移属独立运维流程）。

## Decisions

1. **激活状态表示**  
   - 列 **`is_active BOOLEAN`**；数据库层使用 **部分唯一索引** 保证至多一行激活，例如 PostgreSQL：  
     `CREATE UNIQUE INDEX storage_profiles_one_active ON storage_profiles ((1)) WHERE is_active`。  
   - 激活切换在**单事务**内完成（例如先将全部 `is_active` 置为 false，再将目标行置为 true），避免零激活窗口过长。

2. **凭据加密**  
   - 使用 **`cryptography`**（项目已用）实现 **Fernet** 或 **AES-GCM** 信封；密钥材料为环境变量 **`DEVAULT_STORAGE_CONFIG_MASTER_KEY`**（32-byte URL-safe base64，与命名以最终实现为准）。  
   - API **永不回显**解密后的 `secret_access_key`；更新时仅当请求体提供新密钥字段才重加密覆盖。

3. **运行时解析**  
   - 引入 **`StorageProfileResolver`**（或等价）：读激活 profile 用于**新作业写入**；读 artifact 上的 **`storage_profile_id`** 用于**读/删已有对象**。  
   - 进程内对 boto3 client（或 `LocalStorage` 根路径）做 **TTL 缓存**，避免每条 RPC 解密；配置变更后可依赖短 TTL 或显式缓存版本号。

4. **与部署级 `storage_type` 开关的关系**  
   - **不再**使用单独的环境变量表示 `local` | `s3`；控制面是否走对象存储协议、是否协商 S3 相关能力，**仅以**当前激活 **`storage_profiles.storage_type`** 为准。

5. **控制台门禁**  
   - 路由 **`access`** 使用 **`principal_kind === 'platform'`**（及改密/MFA 门禁与现有 `canAdmin` 组合），**不得**单独依赖 `role === 'admin'` 以免租户管理员看到存储管理页。

## Risks / Trade-offs

- **[Risk] 无激活 profile 时备份失败** → 启动或 `LeaseJobs` 路径明确错误码与文档；可选「开发模式」放宽仅限非生产。  
- **[Risk] 主密钥轮换** → 设计文档记录：需双主密钥或重新加密全表脚本（本变更可先文档化「手动轮换步骤」，自动化列为后续）。  
- **[Risk] 切换激活后旧制品仍在旧桶** → 由 **`storage_profile_id`** 保证正确路由；运营上切换激活不等于数据迁移。  
- **[Trade-off] 删 profile** → 外键 **ON DELETE RESTRICT**；若需软删，加 `deleted_at` 与唯一约束调整。

## Migration Plan

1. 新增 `storage_profiles` 表与索引；**不**插入种子行。  
2. `artifacts` 添加 **可空** **`storage_profile_id`** 与外键 **`ON DELETE RESTRICT`**；历史行保持 **NULL** 直至运营回填（可选）。  
3. 部署应用版本：在控制面创建并激活 profile 后再接备份流量。  
4. 移除租户三列与代码路径；运行期不再从 **`DEVAULT_S3_*`** 解析连接（部署示例可逐步收紧 env）。  
5. **Rollback**：恢复上一版本镜像前需保留 DB 备份；向前滚动失败时依赖 DB 备份。

## Open Questions

- 平台级 **AssumeRole**（非 BYOB）是否仍需要：若需要，字段放在 profile JSON 还是独立列（本提案允许 profile 级 STS 字段，与租户无关）。  
- **`storage_type=local`** 时多 profile 是否有意义（可能仅允许单条或忽略 endpoint）；可在实现中限制 `local` 仅一条或禁止激活非 s3 于生产。
