---
sidebar_position: 5
title: 测试
description: pytest 与 gRPC / 兼容性校验
---

# 测试

## 运行

```bash
pytest -q
python scripts/verify_release_docs.py
python scripts/verify_compatibility_matrix.py
```

`pyproject.toml` 中配置 `testpaths` 与 `pythonpath`。CI **`matrix.suite`** 含 **`compatibility`** 轻量切片，见 [兼容性与版本矩阵](./compatibility.md)。

## gRPC / 生成代码

修改 **`proto/agent.proto`** 后执行 **`bash scripts/gen_proto.sh`**，确认导入与生成的 **`grpc_gen`** 一致。

## 存储后端

依赖 S3 的集成测试在 CI/本地需提供端点；纯逻辑可选用 `local`。
