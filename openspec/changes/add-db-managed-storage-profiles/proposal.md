# Change: 控制面数据库管理对象存储配置（下线 BYOB）

## Why

当前 S3 兼容存储的连接参数与凭证主要来自部署环境变量；租户可通过 BYOB（`tenants.s3_bucket` / AssumeRole）覆盖全局桶与角色。运维希望在控制面统一配置多条全局存储定义、唯一激活、敏感凭据加密落库，并在制品维度记录实际写入的存储实例，同时去掉租户级存储覆盖以降低复杂度与安全暴露面。

## What Changes

- **新增**全局 **`storage_profiles`**（名称可最终实现时微调）：每条记录包含 **`storage_type`**（如 `s3`、`local`，可扩展）、非敏感连接字段、以及使用**部署环境提供的根密钥**加密存储的静态 AK/SK（若该类型需要）；支持 **CRUD**。
- **约束**：同一时刻**恰好一条** profile 为 **激活**状态；新建备份写入 artifact 时使用**当前激活** profile 的 id。
- **BREAKING**：**完全移除 BYOB**——删除租户模型与 API 中的 `s3_bucket`、`s3_assume_role_arn`、`s3_assume_role_external_id`；删除 `effective_s3_bucket` / 租户分支的客户端解析逻辑；控制台租户页不再展示上述字段。
- **`artifacts`** 增加 **`storage_profile_id`**（外键，非空对新写入；迁移期对历史行 backfill），与现有 `storage_backend` 的语义对齐策略在实现中明确（可保留冗余字段以兼容 Agent 能力协商）。
- **下线**（或逐步废弃）控制面进程对 **`DEVAULT_S3_*`** 作为**唯一**配置源的依赖；根加密密钥**仍来自部署环境**（不进库）。
- **控制台**：新增「存储管理」页面（列表 / 创建 / 编辑 / 删除 / 设为激活），**仅 `principal_kind` 为平台的会话**可见且可操作；API 与现有 **`require_admin`（platform）** 对齐。
- **文档与部署清单**：更新 OpenAPI、网站文档、Helm/Compose 示例以反映 DB 配置与 env 精简。

## Capabilities

### New Capabilities

- `platform-storage-profiles`: 平台级存储配置（多 profile、唯一激活、`storage_type`、凭据加密）、制品挂载 `storage_profile_id`、REST 与控制台行为、BYOB 移除后的不变量。

### Modified Capabilities

- （无）现有 `openspec/specs/` 下能力与对象存储无直接需求条目；控制台会话规格不修改，存储门禁在新能力中单独规定。

## Impact

- **数据库**：新表、部分唯一索引或等价「激活指针」、`artifacts` 新列、租户表删列、Alembic 迁移与数据回填脚本。
- **后端**：`Settings` / `s3_client.py` / `factory.py` / `grpc/servicer.py` / `retention.py` / `services/control.py` / `api/schemas.py` / 路由。
- **控制台**：新页面与路由、`access` 与 `principal_kind` 门禁、OpenAPI 类型、国际化文案；租户编辑页删字段。
- **文档**：`website/docs/storage/*`、`website/docs/admin/tenants-and-rbac.md` 等。
- **运维**：引入 **`DEVAULT_STORAGE_CONFIG_MASTER_KEY`**（或项目约定之正式名称）等环境变量；首次部署在控制面**手动创建并激活**首条 profile（迁移不插入种子行）。
