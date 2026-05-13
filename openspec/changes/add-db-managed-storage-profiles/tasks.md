## 1. 规格与校验

- [x] 1.1 运行 `npx @fission-ai/openspec@latest validate add-db-managed-storage-profiles --strict` 并修复全部校验错误

## 2. 数据库与模型

- [x] 2.1 新增 Alembic 迁移：创建 **`storage_profiles`** 表（含 **`storage_type`**、连接字段、**`is_active`**、加密凭据列、时间戳等）及 **「至多一条激活」** 部分唯一索引
- [x] 2.2 迁移：为 **`artifacts`** 增加 **`storage_profile_id`**（可空 + 外键 **`ON DELETE RESTRICT`**；无默认种子回填）
- [x] 2.3 迁移：删除 **`tenants`** 上 **`s3_bucket` / `s3_assume_role_arn` / `s3_assume_role_external_id`** 列；更新 SQLAlchemy **`Tenant`** / **`Artifact`** 模型
- [x] 2.4 无环境种子：首条 **`storage_profiles`** 由控制面（控制台/API）创建；**`artifacts.storage_profile_id`** 可为 **NULL**（读/保留清理对 NULL 回退到当前激活 profile）

## 3. 加密与解析服务

- [x] 3.1 实现根密钥读取（**`DEVAULT_STORAGE_CONFIG_MASTER_KEY`** 或最终命名）与 **Fernet/AES-GCM** 加解密工具，仅用于存储 profile 密文字段
- [x] 3.2 实现 **`StorageProfileResolver`**（或等价）：查询激活 profile、按 **`storage_profile_id`** 加载指定 profile；带 **TTL 缓存** 与失效策略
- [x] 3.3 将 **`build_s3_client` / `get_storage`** 改为基于 profile（移除 **`build_s3_client_for_tenant`** / **`effective_s3_bucket`** / **`get_storage_for_tenant`** 的租户分支或删除并全量替换调用点）

## 4. 控制面 API

- [x] 4.1 新增 **`/api/v1/storage-profiles`**（或约定路径）**CRUD** + **「设为激活」** 子资源/动作；全部 **`Depends(require_admin)`**
- [x] 4.2 OpenAPI / **Pydantic** schema：创建/更新体、列表/详情 DTO；**不回显** secret
- [x] 4.3 从 **`TenantPatch` / `TenantOut`** 与 **`patch_tenant`** 移除 BYOB 字段；同步 **`openapi.json`** 生成物与 **`console` api-types**

## 5. gRPC、调度与作业收尾

- [x] 5.1 更新 **`grpc/servicer.py`**：预签名 / multipart / 完成与验证路径使用 **激活 profile** 或 **artifact 上 `storage_profile_id`**
- [x] 5.2 写入 **`Artifact`** 时设置 **`storage_profile_id`**（及与 **`storage_backend`** 一致性策略）
- [x] 5.3 更新 **`retention`** 与其它 **`get_storage_for_tenant`** 调用方为按制品或租户上下文解析 profile（无租户桶覆盖）

## 6. 配置与部署

- [x] 6.1 精简 **`Settings`**：移除或标记废弃仅用于旧 env 直配 S3 的字段；文档说明与 **`storage_profiles`** 的优先级
- [x] 6.2 更新 **`deploy/docker-compose.yml`**、**`deploy/helm/**`** 示例：注入根加密密钥；移除或注释 **`DEVAULT_S3_*`** 与 MinIO 示例的对齐说明

## 7. 控制台

- [x] 7.1 新增 **`/platform/storage`**（或同级）路由与菜单；**`access`** 条件包含 **`principal_kind === 'platform'`**（并与改密/MFA 门禁一致）
- [x] 7.2 实现列表、创建/编辑表单（密钥可选更新）、删除（受外键约束）、设为激活
- [x] 7.3 从 **`platform/tenants`** 表单移除 S3/BYOB 字段；更新 **zh-CN / en-US** 文案

## 8. 文档与测试

- [x] 8.1 更新 **`website/docs/storage/*`**、**`tenants-and-rbac.md`**、ER/架构文档，删除 BYOB 描述
- [x] 8.2 单测：加密往返、激活唯一性、解析器缓存、API 403（租户 JWT）、artifact 外键
- [x] 8.3 集成/E2E（若已有 harness）：覆盖创建 profile → 激活 → 备份写入带 **`storage_profile_id`**（沿用现有 gRPC/备份用例与迁移种子即可在 CI 验证）
