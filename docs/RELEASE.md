# 发版检查清单（模板）

> 复制本页为「版本 x.y.z 发版笔记」或在 PR 描述中逐项勾选。与 **`website/docs/development/releasing.md`**、`**scripts/bump_release.py**` 及 **`CHANGELOG.md`** 配合使用。

## 1. 升级顺序

- [ ] **确认依赖方向**：先升级 **控制面**（API + gRPC + 迁移），再滚动 **Agent**；或按 `docs/compatibility.json` 中矩阵说明的例外执行。
- [ ] **数据库**：在控制面镜像上线前或按零停机流程执行 **`alembic upgrade head`**（见 `website/docs/install/database-migrations.md`）。
- [ ] **对象存储**：无自动建桶；确认桶与 IAM 已就绪。

## 2. 兼容性与契约

- [ ] 已更新 **`docs/compatibility.json`** 中 **`current.control_plane_release`**（及必要时的 **`matrices`**）。推荐使用 **`python scripts/bump_release.py`** 与 **`pyproject.toml`** 同步写入。
- [ ] CI 通过 **`scripts/verify_compatibility_matrix.py`** 与 **`scripts/verify_release_docs.py`**。
- [ ] 若修改 **`proto/agent.proto`**：已执行 **`bash scripts/gen_proto.sh`**，且 Agent 与控制面制品来自兼容矩阵。

## 3. 已知不兼容与迁移

- [ ] **CHANGELOG** 中已列出破坏性变更及迁移步骤（链接到本节或独立设计文档）。
- [ ] **gRPC**：若 bump **`devault.agent.v2`**（示例），需同步 Agent 重生成 stub 与发布说明。

## 4. 观测与密钥

- [ ] **环境变量**：生产 **`DEVAULT_API_TOKEN`**、**`DEVAULT_GRPC_REGISTRATION_SECRET`**（若启用）、S3 凭证等已轮换或复核。
- [ ] **TLS / 网关**：生产 gRPC 走 TLS 或 Envoy 等（见 `website/docs/security/tls-and-gateway.md`）。

## 5. 回滚

- [ ] 回滚控制面镜像到上一标签；**Alembic**：若新迁移不可逆，准备 `downgrade` 或从备份恢复元数据库（见运维 Runbook）。
- [ ] Agent 回滚到与当前控制面矩阵兼容的版本（见 **`docs/compatibility.json`**）。

## 6. 发布后验证

- [ ] **`GET /healthz`**、**`GET /version`**（含 `git_sha` 若配置）。
- [ ] Agent 一次 **Heartbeat** 日志无 **`AGENT_VERSION_*`** 致命错误；抽查 **`server_capabilities`** 与存储后端一致。
- [ ] （建议）在默认分支手动运行 **`.github/workflows/e2e-version-matrix.yml`**（Compose + **Register** / **Heartbeat** 冒烟）。若需「当前控制面 + 上一 MINOR Agent」等交叉行，先将 **`docs/compatibility.json`** · **`ci_e2e.previous_minor_git_ref`** 设为可解析的 git ref（例如 **`v0.3.0`** tag）并合并后再跑；详见 **`website/docs/development/compatibility.md`**。
