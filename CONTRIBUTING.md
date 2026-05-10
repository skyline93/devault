# Contributing to DeVault

## Pull requests

- **Tests**：`pytest` 通过；涉及兼容矩阵时注意 **`matrix.suite`**。
- **CHANGELOG**：用户可见的 HTTP/gRPC/控制台行为变化写入 **`CHANGELOG.md`** **`[Unreleased]`**（中文或英文均可，保持与既有条目风格一致）。
- **§十四 / E-UX-001（十四-16）**：若 PR 触及 **`src/devault/api/schemas.py`** 中面向用户的模型（如 **`JobOut`**、**`PolicyOut`**、**`TenantOut`**）或 **`console/`** 中对应 REST 调用，请确认 **Ant Design Pro 控制台**已同步或已在 **`website/docs/guides/web-console.md`** 登记豁免。
- **OpenAPI ↔ 控制台（十四-17）**：**`JobOut` / `PolicyOut`** 等变更时，同步 **`console/`** 列表/表单与 **`access.ts`** 只写语义；CI 在导出 **`openapi.json`** 后运行 **`python scripts/verify_console_openapi_contract.py`**，并在 **`console/`** 执行 **`npm run codegen`** 与 **`npm run build`**。

## 本地检查

```bash
pip install -e ".[dev]"
pytest -q
python scripts/verify_release_docs.py
python scripts/verify_compatibility_matrix.py
python scripts/export_openapi_json.py -o console/openapi.json
python scripts/verify_console_openapi_contract.py console/openapi.json
cd console && npm ci && npm run codegen && npm run build
```

## 文档站

网站源码在 **`website/`**；侧栏见 **`website/sidebars.ts`**。
