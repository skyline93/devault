---
sidebar_position: 6
title: 发版与变更记录
description: SemVer、bump 脚本与 CI
---

# 发版与变更记录

## 版本号 SSOT

以 **`pyproject.toml`** **`[project].version`** 为准；推荐使用 **`scripts/bump_release.py`** 同步 **`CHANGELOG.md`**、**`docs/compatibility.json`** 中 **`current.control_plane_release`**。

运行时 **`GET /version`** / **`devault.__version__`** 来自安装包元数据或 **`pyproject.toml`**。

## CHANGELOG

根目录 **`CHANGELOG.md`**，Keep a Changelog；发版须有与版本一致的小节（**`verify_release_docs.py`** 校验）。

## bump 脚本

```bash
python scripts/bump_release.py <新版本号>
# python scripts/bump_release.py 0.5.0
```

可使用 **`--dry-run`**。**`--date`** 可覆盖小节日期。

## proto 变更

若修改 **`proto/agent.proto`**：**`bash scripts/gen_proto.sh`**，并核验控制面 / Agent / [兼容性与版本矩阵](./compatibility.md) 与 **[gRPC（Agent）](../reference/grpc-services.md)**。

## 文档站

产品或运营相关说明须在 **`website/docs/`** 维护；内核契约与兼容性以仓库 **`docs/compatibility.json`** 与源码为准。

## CI

`.github/workflows/ci.yml`：安装包后 **`verify_release_docs.py`**、`pytest`。详见源码树内工作流文件。
