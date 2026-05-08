# DeVault 文档站（Docusaurus）

本目录为 DeVault 的 **Docusaurus 3** 站点，与信息架构说明对照实现，正文位于 `docs/`。

## 前置条件

- **Node.js ≥ 20**（见 `package.json` 的 `engines`；可使用 `.nvmrc`）
- npm（随 Node 安装）

## 常用命令

在 **`website/`** 目录下执行：

| 命令 | 说明 |
|------|------|
| `npm ci` | 按 lockfile 安装依赖（CI 推荐） |
| `npm install` | 日常安装依赖 |
| `npm start` | 启动开发服务器（默认 <http://localhost:3000>），热更新 |
| `npm run build` | 生产构建，输出到 `build/` |
| `npm run serve` | 在本地静态服务已构建的 `build/`（用于验收生产包） |
| `npm run typecheck` | TypeScript 检查 |

## 部署前检查

1. 若使用自有域名，修改根目录 **`docusaurus.config.ts`** 中的 `url` 与 `baseUrl`（子路径部署时 `baseUrl` 常为 `/仓库名/`）。
2. 「编辑此页」链接依赖 `editUrl` 与默认分支名（当前为 Gitee `dev` 分支）；若主分支改名，请同步修改配置中的常量。

## 与仓库其他部分的关系

- 产品设计与旧稿归档见仓库根目录 **`docs-old/`**（**不是**本站内容源）。
- 用户文档以 **`website/docs/`** 为准；发版时记得同步更新文档与根目录 `CHANGELOG.md`。
