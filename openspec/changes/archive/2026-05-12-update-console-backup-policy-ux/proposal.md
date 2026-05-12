# Change: 控制台备份策略新建 / 列表 / 编辑体验优化

## Why

当前「备份策略」在控制台中新建与编辑流程分散（多 Tab、备份计划需先保存策略后再建），启用状态仅能在编辑页切换，且新建时「加密上传制品」未默认开启。同时希望 **Agent 以主机名对用户可见**，减少 UUID 作为主展示；执行面列表与策略绑定交互一致。

## What Changes

- **新建策略单页化**：策略名称、文件备份配置、执行绑定（`bound_agent_id`）与**可选的一条**关联备份计划（Schedule）在同一页完成；布局**紧凑**，在桌面宽度下**相关字段可并排（栅格）排布**，避免整页「单列堆叠 + 右侧大面积留白」。
- **新建时默认可选一条备份计划**：用户可在同一提交流程中创建 0 或 1 条计划；不配计划仍可创建策略。
- **新建默认开启「加密上传制品」**：新建策略表单中 `encrypt_artifacts`（或等价配置）默认开启；用户仍可手动关闭。
- **新建与编辑表单不展示「启用」开关**：创建策略时**固定按启用状态提交**（`enabled: true`）；编辑抽屉内**不提供**策略级启用/禁用控件，启停**仅在列表**完成。
- **策略列表启用控件置于操作列**：对具备写权限的用户，启用/禁用 **Switch（滑钮）放在「操作」列内**（与编辑、删除等并列），**不设独立的「启用」列**；切换前仍须**二次确认**；成功后列表刷新。无写权限用户可通过操作列内只读展示（如 Tag）或表格其他信息感知状态，具体实现以保持列表可扫读为准。
- **编辑策略右侧抽屉**：从整页编辑改为右侧 Drawer；保存成功后**自动刷新策略列表**，**抽屉保持打开**。
- **编辑时路径与 Agent 只读**：在编辑抽屉中，备份路径（`config.paths` 等路径输入）与绑定的执行组件（`bound_agent_id`）**置灰且不可编辑**，适用于**所有策略状态**（启用/禁用等）；约束以**前端页面为准**（建议后端仍校验以防绕过）。
- **抽屉内「关联备份计划」表格**：**不设独立「启用」列**；**启用**以 **Switch（滑钮）** 放在**操作列**，通过 `PATCH /api/v1/schedules/{id}` 更新 `enabled`；切换前**二次确认**（与策略列表启停交互一致）。操作列提供 **「编辑」**（修改 cron、timezone 等，见 `design.md`）。**移除**行内指向外部「计划管理」的链接（不要求用户跳转至合规计划总表完成本策略下的操作）。
- **Agent 对用户呈现主机名**：`agent_id` / `bound_agent_id` 作为应用内技术标识**不向用户作为主展示**；界面主文案与表格主列以 **Agent 主机名**（`hostname` 或 API 等价字段）为主；缺省主机名时可用受控回退（如短 ID 占位，见 `design.md`）。
- **策略列表「Agent 主机」列**：原「绑定执行组件」列更名为 **Agent 主机**（或 i18n 等价），单元格展示**主机名**而非 UUID。
- **新建/编辑策略中的 Agent 选择**：字段标签改为 **Agent 主机**；`Select` 仅展示**主机名**选项（值仍为 `bound_agent_id`）；**移除**选择框下方「租户内执行组件」外链按钮。
- **执行面租户 Agent 与全舰队列表**：表格**移除「执行组件 ID」列**；以 **主机名** 为主列且可点击；点击后在**右侧抽屉**展示该 Agent 的**快照/详情信息**（与现有详情能力对齐或复用 `execution/fleet/detail` 数据模型，见 `design.md`）。
- **作业中心（备份作业列表）**：**移除「租约主机」列**；**「完成主机」列**更名为 **「Agent 主机」**（展示 `completed_agent_hostname` 等既有字段）；**移除表格「错误」列**，错误信息改在**右侧作业详情抽屉**中展示（有则展示，无则省略）。
- **策略列表列顺序**：**「创建时间」列置于第一列**（先于名称等其余列）。

## Impact

- **Affected specs**: 能力 `console-backup-policy-ux`（本变更 delta，含修订）。
- **Affected code（预期）**:
  - `console/src/pages/backup/policies/index.tsx` — **创建时间**列置于首位；**Agent 主机**列；**操作列内**启用 Switch、确认弹窗、刷新与抽屉协调（无独立「启用」列）。
  - `console/src/pages/backup/policies/edit.tsx`、`PolicyFormFields.tsx`、`PolicyEditDrawer.tsx` — 去掉表单内「启用」项；新建提交固定 `enabled: true`；**紧凑栅格/并排**布局；**抽屉内计划表**：操作列 **Switch + 编辑 + 删除**，去掉「计划管理」外链；**Agent 下拉仅主机名、无外链**。
  - `console/src/pages/backup/jobs/index.tsx` — 作业表去掉租约/错误列；**Agent 主机**列（原完成主机字段）；详情抽屉展示错误信息；列表与抽屉文案与 i18n 对齐。
  - `console/src/pages/execution/tenant-agents/index.tsx`、`console/src/pages/execution/fleet/index.tsx`（及必要时的 `detail.tsx` 逻辑抽取）— 去掉 ID 列；主机名点击打开**右侧抽屉**快照。
  - `console/config/config.ts` — 路由与重定向（若已有）保持或由 design 约定。
  - `console/src/locales/zh-CN.ts`、`console/src/locales/en-US.ts` — 文案随布局与列调整更新。
- **API**: 新建仍 `POST` 策略（`enabled: true`）；列表启停仍 `PATCH` 策略；编辑抽屉内策略 `PATCH` 不传策略级 `enabled`；备份计划行使用已有 **`PATCH /api/v1/schedules/{schedule_id}`**（`SchedulePatch`：`cron_expression`、`timezone`、`enabled` 等可选字段）。

## Non-Goals

- 不改变「每策略多条备份计划」的后端能力；仅**新建流程限制最多一条**。
- 不在本变更中要求后端新增「单请求原子创建策略+计划」接口（若已有可择优采用）。
