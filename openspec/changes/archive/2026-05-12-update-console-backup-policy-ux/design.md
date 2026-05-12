## Context

控制台备份策略当前实现要点（代码侧）：

- 路由：`/backup/policies/new` 与 `/backup/policies/:policyId` 均挂载 `console/src/pages/backup/policies/edit.tsx`，新建与编辑共用组件，新建使用 Tabs（基本 / 文件备份配置 / 执行绑定）。
- 备份计划：通过 `/api/v1/schedules` 加载，编辑态按 `policy_id` 过滤；新建时无 `policy_id`，计划通常在保存策略后再建。
- 新建表单初始：`enabled: true`，`encrypt_artifacts` 来自 `parseConfig`，新建空配置时为关闭。

本设计在**不强制后端改版**的前提下，优先用前端组合与交互满足需求。

## Goals / Non-Goals

**Goals**

- 新建：单页展示名称、备份配置、执行绑定；可选 0/1 条备份计划；`encrypt_artifacts` 新建默认开启；**表单不出现启用开关**，提交 **`enabled: true`**。
- 新建与编辑：**紧凑布局**，相关字段 **Ant Design `Row`/`Col` 或 `Form` 栅格** 并排，减少右侧留白；小屏仍纵向堆叠可滚动。
- 列表：**启用 Switch 仅在操作列**，不设单独「启用」列；二次确认 + 成功后刷新。
- 编辑：Drawer 承载表单；**无策略级启用开关**；路径与 `bound_agent_id` 全状态只读；保存后刷新列表且 Drawer 不关闭；抽屉内**备份计划表**按 **§6** 交互（操作列 Switch + 编辑、无「计划管理」外链）；**Agent 绑定区**按 **§7** 仅展示主机名为主、无 ID 主列与无租户 Agent 外链。
- **执行面**：租户内 Agent 与全舰队列表按 **§7** 以主机名为入口、抽屉看快照。

**Non-Goals**

- 不在此设计稿中规定视觉稿像素级规范；由实现选用现有 Ant Design / ProComponents 模式保持一致性。
- 不扩展「新建多条计划」。

## Decisions

### 1. 新建可选一条备份计划的提交顺序

**决策**：若 Schedule 创建 API 要求已有 `policy_id`，则用户点击保存时顺序为：

1. `POST /api/v1/policies`（或现有创建接口）创建策略；
2. 若用户填写了计划字段（如 cron、timezone、enabled），则 `POST` 创建一条 Schedule 且 `policy_id` 为新策略 id；
3. 任一步失败则整体提示错误；若策略已创建而计划失败，应明确提示并引导用户在编辑抽屉中补建（可选增强：提供「重试创建计划」）。

**新建启用**：请求体中 **`enabled` 固定为 `true`**，不暴露表单控件。

**备选**：若后端提供原子「策略+单计划」接口，可改为单次请求并在此设计替换为首选。

### 2. 编辑抽屉与路由

**决策 A（推荐）**：策略列表页（`policies/index.tsx`）为「列表 + Drawer」容器：点击编辑打开 Drawer，内嵌原表单逻辑或抽取共享 `PolicyForm`；URL 可使用 query `?edit=<policyId>` 便于刷新后恢复（可选）。

**决策 B**：保留 `/backup/policies/:id` 路由但组件渲染为带 Drawer 的列表父级（layout 包裹），复杂度较高。

默认采用 **决策 A** 或 **列表页内 Drawer + 不改变 URL**，以减少路由重构；若团队偏好可分享链接打开编辑，再采用 query 方案。

### 3. 只读字段（编辑抽屉）

**决策**：编辑模式下对以下控件设置 `disabled` + 视觉置灰（或 `readOnly` 对 Input 的适用控件），且不向提交 payload 写入变更（或写入原值）：`config.paths` 文本域、与路径直接相关的编辑（若「排除规则」是否只读——**本需求仅明确路径与 Agent**；排除规则默认可编辑，除非产品另行收紧）。

**决策**：`bound_agent_id` 的 `Select` 在编辑态 `disabled`，展示当前 Agent。

**决策**：编辑抽屉 **不包含** 策略级「启用」表单项；`PATCH` 不传 `enabled` 除非未来单独做「抽屉内启停」（当前不做）。

### 4. 列表启用 Switch 与确认（修订）

**决策**：启用/禁用 **Switch 放在 `ProTable` 的「操作」列**内（与编辑、删除同一列），**删除独立「启用」列**，避免与「操作」重复占宽。

**决策**：Switch 仍作意图入口；`onChange` 时若与当前服务端状态一致则忽略；否则弹出 `Modal.confirm`（启用/禁用不同 `title`/`content`），确认后 `PATCH`，成功后 `actionRef.current?.reload()`。

**只读用户**：操作列可展示启用状态的 **Tag 文本**（无 Switch），或依赖名称旁信息；以保持列表可读为准。

取消确认时 Switch 回滚（受控 `checked` 绑定服务端状态）。

### 5. 表单布局（新增）

**决策**：新建页与编辑抽屉内表单使用 **`Row` + `Col`（如 `xs={24}` `md={12}`）** 或等价栅格：例如「名称」与「执行绑定」可同排；备份布尔开关、数字输入等**成组并排**；路径/排除等大文本仍占满行。目标为**中等视口以上显著减少右侧空白**。

### 6. 策略抽屉内「关联备份计划」表格（修订）

**决策**：表格**删除独立「启用」列**；`enabled` 的变更通过 **操作列内的 `Switch`（滑钮）** 完成，受控绑定当前行服务端状态；`onChange` 意图与策略列表一致：**二次确认**后调用 `PATCH /api/v1/schedules/{schedule_id}`，body 仅 `{ enabled: boolean }`（或与其它字段组合时仍以本次切换为准），成功后刷新抽屉内计划列表（及全局 schedules 缓存若存在）。

**决策**：操作列提供 **「编辑」** 按钮：打开 Modal（或等价），表单字段至少含 **cron_expression、timezone**；提交时 `PATCH` 同一 `schedule_id`。**启用状态不在编辑弹窗内与 Switch 重复**（避免双入口）；若编辑弹窗沿用旧组件含 `enabled` 字段，实现时应移除或禁用，以操作列 Switch 为唯一启停入口。

**决策**：**移除**行内「计划管理」外链（原跳转 `/compliance/schedules` 等）；本策略下的计划增删改均在抽屉内闭环。

**只读用户**：无写权限时操作列不展示 Switch；启用状态以 **Tag** 等形式与编辑/删除的可见性规则一致（删除通常亦隐藏）。

### 7. Agent 标识对用户呈现为「主机名」

**原则**：`id` / `bound_agent_id` 为系统绑定与 API 载荷字段；**用户可见主文案与表格主列**为 **主机名**（`TenantScopedAgentOut.hostname` 或等价）。若主机名为空，**SHALL** 使用明确回退（如「未上报主机名」+ 可选 Tooltip 展示 ID，或产品规定的短格式），避免把长 UUID 当作主标签。

**策略列表**：列标题由「绑定执行组件」改为 **「Agent 主机」**（i18n）；单元格通过 `bound_agent_id` 在租户 Agent 列表中解析 **hostname** 展示；无匹配时回退。

**新建/编辑策略表单**：字段标签 **「Agent 主机」**；`Select` 的 `options` **label 仅主机名**（`value` 仍为 agent id）；**移除**「租户内执行组件」外链（用户不依赖该链完成绑定）。

**执行面 — 租户内执行组件页、全舰队页**：表格 **移除独立「执行组件 ID」列**；主识别列为 **可点击的主机名**；点击后 **右侧 Drawer** 打开，内容与「组件快照/详情」一致（复用或抽取 `execution/fleet/detail` 所用数据请求，如 `GET .../agents/{id}` 或现有 OpenAPI 操作，以实现为准）。

### 8. 作业中心（备份作业）列表与详情抽屉

**决策**：`ProTable` **不再展示「租约主机」列**；作业详情抽屉内 **亦不单独展示租约主机行**（与列表一致，避免重复；需要时仍可从 `config_snapshot` / `result_meta` 中查看）。

**决策**：原「完成主机」列表列标题改为 **「Agent 主机」**（i18n），`dataIndex` 仍为 `completed_agent_hostname`（或等价字段）。

**决策**：列表 **移除「错误」列**；作业 `error_message`（或等价）在用户打开 **右侧详情 Drawer** 时展示（独立区块或并入结果元数据上方，需可读、可复制/换行友好）。

### 9. 策略列表列顺序

**决策**：备份策略列表 `ProTable` 的 **第一列**为 **创建时间**（`created_at`），其后为名称、插件、Agent 主机等其余列。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| 策略创建成功但计划创建失败 | 明确错误文案；列表已可见新策略，用户可进编辑抽屉补计划 |
| 仅前端禁用路径/Agent，API 仍接受修改 | 需求限定页面；后续可加后端校验 |
| Drawer 内长时间编辑与列表数据陈旧 | 保存后 `reload`；打开 Drawer 时可 `request` 单条 policy 刷新表单 |
| 策略列表操作列过宽 | 使用 `Space`/`size="small"`，必要时 `ellipsis` 或折叠次要操作 |
| 抽屉内计划表操作列过宽 | `Space`/`size="small"`；必要时 Cron 列 `ellipsis` |
| 主机名未上报 | 回退文案 + Tooltip 可选展示 ID；运维侧督促 Agent 上报 hostname |
| 作业列表信息变少 | 详情抽屉承担错误与次要字段；必要时加「复制 JSON」 |

## Migration Plan

- 纯前端行为与路由调整；无数据迁移。
- 发布后对已习惯「全页编辑」的用户：编辑入口仍在列表，形态变为抽屉。

## Open Questions

- 「排除规则」等其它配置是否在编辑抽屉中也应只读：当前**未**纳入需求；若需对齐「路径不可变」语义可后续单开变更。
