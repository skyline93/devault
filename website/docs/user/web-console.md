---
sidebar_position: 8
title: Web 控制台
description: 入口、认证与能力范围
---

# Web 控制台

## 入口

**主入口（企业交付）**：仓库 **`console/`**（**Ant Design Pro**；人机 **Cookie 会话**，可选 **Bearer** + **`X-DeVault-Tenant-Id`**）。在 **`console/`** 执行 **`npm run dev`**（默认 **`http://localhost:8010`**，**`/api`**、**`/docs`**、**`/version`** 等代理到 **`127.0.0.1:8000`**）。**登录**：**`/user/login`**（**邮箱 + 密码** 走 IAM 或历史 Cookie 路径，若策略要求则 **TOTP 第二步**）；**Bearer / 自动化**：**`/user/integration`**；**重置密码** **`/user/reset-password`**、**邮件邀请接受** **`/user/accept-invite?token=`**（§十六-11）。**自助注册已移除**（账号由 IAM 引导 CLI / 平台 API 创建）。默认进入 **`/overview/welcome`**；顶栏 **租户选择器** 将所选租户 UUID 写入 **`localStorage`**（**`devault_tenant_id`**）并由请求拦截器注入 **`X-DeVault-Tenant-Id`**（业务 API **必填**）。**租户管理员** 在 **概览 · 成员邀请** 向邮箱发送 **`POST /api/v1/tenants/{tenant_id}/invitations`**。主要路由示例：**`/backup/jobs`**、**`/backup/policies`**、**`/backup/artifacts`**、**`/compliance/schedules`**、**`/execution/fleet`**、**`/platform/tenants`**（仅 admin 菜单）。

**容器 / K8s**：见 **`deploy/docker-compose.yml`**（**`--profile with-console`**，镜像 **`deploy/Dockerfile.console`**）与 **`deploy/helm/devault`**（**`console.enabled`**）。详见 [Web 控制台与 REST 交付节奏](../guides/web-console.md)。

## 认证

**推荐**：在 **`/user/login`** 使用 **邮箱 + 密码**（及租户策略要求的 **TOTP**），由控制面签发 **httpOnly** 会话 Cookie（**Redis**），浏览器请求 **`/api`** 时 **`credentials: 'include'`**，写操作携带 **CSRF**（**`X-CSRF-Token`** + **`devault_csrf`** Cookie）。未完成 MFA 时 **`GET /auth/session`** 可能返回 **`needs_mfa: true`**，此时控制台不授予写菜单权限，直至 **`POST /api/v1/auth/mfa/verify`**。

**自动化 / 应急**：在 **`/user/integration`** 录入 **Bearer**（**`localStorage`**），与 REST 一致。**非**浏览器 HTTP Basic 弹窗。

**运维引导**：首次人机账号使用 **`devault-admin create-console-user --email … --password … --tenant <UUID> --role tenant_admin`**（需已存在租户；密码 ≥ 12 字符）。

## 能力范围

**`console/`** 已覆盖与 **`/api/v1/*`** 对齐的作业、策略、备份/预检、制品（含恢复/演练与 Legal hold）、两套 Cron、租户内 Agent、Agent 池与成员、全舰队与登记/吊销、租户管理员 PATCH 等（与 **`docs-old/enterprise-backlog.md`** **十五-11～十八** 一致）。

**作业列表筛选（十五-23）**：作业中心调用 **`GET /api/v1/jobs`** 时可带 **`kind`**、**`status`** 与分页 **`limit` / `offset`**，由服务端过滤。

**发起备份向导（十五-24）**：**`/backup/run`** 使用分步 **Steps**（选择策略或内联 JSON → 填写参数 → 确认并入队）。

**指标与 Grafana（十五-24）**：**`/overview/workbench`** 提供 **Prometheus 指标（`/metrics`）** 外链；若构建时设置 **`UMI_APP_GRAFANA_URL`**，显示 **打开 Grafana** 按钮。与 [可观测性](../install/observability.md) 文档一致。

复杂自动化与批量变更仍可配合 **HTTP API**、**CLI** 或上层平台使用。

## 冒烟测试（十五-22）

仓库根或 **`deploy/`** 下启动专用 Compose（从源码构建控制面与控制台）后，在 **`console/`** 执行 **`npm ci`**、**`npx playwright install chromium`**、**`npm run test:e2e`**（默认 **`E2E_BASE_URL=http://127.0.0.1:8080`**；冒烟在 **`/user/integration`** 粘贴与 Compose 一致的 **`DEVAULT_API_TOKEN`**）。详见 **`console/README.md`** 与 **`.github/workflows/console-e2e.yml`**。

## 与租户作用域的关系

SPA 通过顶栏租户选择与 **`X-DeVault-Tenant-Id`** 显式作用域；REST 与浏览器一致，**不得**省略该头（无默认 slug 回落）。详见 [租户与访问控制](../admin/tenants-and-rbac.md)。
