---
sidebar_position: 3
title: 测试
description: pytest 与 gRPC 相关注意点
---

# 测试

## 运行

```bash
pytest -q
```

`pyproject.toml` 中配置了 `testpaths` 与 `pythonpath`，确保在仓库根执行。

## gRPC / 生成代码

- 修改 `proto/agent.proto` 后务必重新执行 **`bash scripts/gen_proto.sh`**
- 提交前确认生成文件与手写代码的导入方式一致

## 存储后端

集成测试若依赖 S3，请在 CI 或本地提供兼容端点；纯逻辑测试可使用 `local` 后端减轻依赖。
