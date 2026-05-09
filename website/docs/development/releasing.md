---
sidebar_position: 4
title: 发版与变更记录
description: 版本号 SSOT、CHANGELOG 与发版脚本
---

# 发版与变更记录

## 版本号（单一事实来源）

**唯一需要手改版本号的地方**：仓库根目录 **`pyproject.toml`** 中 `[project]` → **`version`**（SemVer）。

运行时 **`devault.__version__`**（以及 `GET /version`、Agent 启动日志等）按以下顺序解析：

1. 已安装发行包：**`importlib.metadata.version("devault")`**（与 wheel/sdist 元数据一致，推荐生产镜像构建路径）。
2. 仅有源码树、未安装元数据时（例如本地 **`pytest`** 且 `pythonpath = ["src"]`）：读取仓库根 **`pyproject.toml`** 的同一字段。

不要在其他文件里再写一份发行版号字符串；文档若需写示例版本，请表述为「与 `pyproject.toml` 一致」或引用上述端点。

## CHANGELOG

人类可读的变更摘要写在仓库根 **`CHANGELOG.md`**。建议遵循 [Keep a Changelog](https://keepachangelog.com/) 风格，与 tag 或发版节奏对齐。

发版前，**`CHANGELOG.md` 必须包含**与 `pyproject.toml` 版本一致的节标题，形如 `## [0.4.0]`（后可接 ` - YYYY-MM-DD`）。仓库提供校验脚本（亦在 CI 中运行）：

```bash
python scripts/verify_release_docs.py
```

若缺少对应小节，脚本以非零退出码失败。

## 一键折叠 Unreleased 并 bump 版本

在 **`[Unreleased]`** 下写好本次发布的条目（至少一条 **`- ...`** 列表项）后，执行：

```bash
python scripts/bump_release.py <新版本号>
# 例如：python scripts/bump_release.py 0.5.0
```

脚本会：

1. 将 **`[Unreleased]`** 与紧随其后的 **`---`** 之间的正文，折叠为新小节 **`## [<新版本>] - <日期>`**（日期默认当天，可用 **`--date YYYY-MM-DD`** 覆盖）。
2. 在文件顶部重置空的 **`[Unreleased]`** 模板（含各 Keep a Changelog 分类小节）。
3. 更新 **`pyproject.toml`** 中的 `version`。

使用 **`--dry-run`** 可只打印将要执行的操作、不写文件。

## CI

**`.github/workflows/ci.yml`** 在安装可编辑包后执行 **`verify_release_docs.py`** 与 **`pytest`**，避免「只改了版本号却忘记 CHANGELOG」进入主分支。

## 与 Agent 的 proto 变更

若本次发布修改了 **`proto/agent.proto`**（含 Heartbeat / Register 等消息字段），发版前请在仓库根执行 **`bash scripts/gen_proto.sh`**，并确保 **控制面镜像与 Agent 制品** 来自同一提交或兼容矩阵（见 [兼容性与版本矩阵](./compatibility.md) 与 [gRPC 服务参考](../reference/grpc-services.md)）。

发版前同步更新 **`docs/compatibility.json`**（至少 **`current.control_plane_release`**），并跑通 **`python scripts/verify_compatibility_matrix.py`**。

## 文档站

用户面向的说明性改动应同步更新 **`website/docs/`** 下对应页面，避免仅更新 README 或 CHANGELOG 之一。
