# Contributing to DeVault

## Pull requests

- **Tests**：`pytest` 通过；涉及兼容矩阵时注意 **`matrix.suite`**。
- **CHANGELOG**：用户可见的 HTTP/gRPC/Web UI 行为变化写入 **`CHANGELOG.md`** **`[Unreleased]`**（中文或英文均可，保持与既有条目风格一致）。
- **§十四 / Web UI（E-UX-001 · 十四-16）**：若 PR 触及 **`src/devault/api/schemas.py`** 中面向用户的模型（如 **`JobOut`**、**`PolicyOut`**、**`TenantOut`**）或 **`src/devault/web/templates/`**，请确认 **`/ui/*`** 已同步或已在 **`website/docs/guides/web-console.md`** 登记豁免。
- **OpenAPI ↔ UI（十四-17）**：修改 **`JobOut` / `PolicyOut`** 等时，更新对应 **Jinja** 列表/详情列或只读提示；**`auditor`** 不得出现可提交的写操作按钮（写操作依赖 **`require_write_ui`**，模板侧应隐藏按钮）。CI 运行 **`python scripts/verify_ui_openapi_registry.py`**。

## 本地检查

```bash
pip install -e ".[dev]"
pytest -q
python scripts/verify_release_docs.py
python scripts/verify_compatibility_matrix.py
python scripts/verify_ui_openapi_registry.py
```

## 文档站

网站源码在 **`website/`**；侧栏见 **`website/sidebars.ts`**。
