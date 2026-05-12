import { defineConfig } from '@umijs/max';

import defaultSettings from './defaultSettings';

/** Dev-only: Umi ``proxy`` targets (``npm run dev``). Production uses nginx ``console-spa.conf.template``. */
const devApiOrigin = (process.env.UMI_DEV_API_ORIGIN || 'http://127.0.0.1:8000').replace(/\/$/, '');
const devIamOrigin = (process.env.UMI_DEV_IAM_ORIGIN || 'http://127.0.0.1:8100').replace(/\/$/, '');

/**
 * 打入 SPA 的 `[devault:auth]` 调试开关：仅当显式 `UMI_APP_AUTH_DEBUG=0|false|off|no` 时为关，否则为开。
 * Docker 构建阶段常为 `NODE_ENV=production` 且若未传 ARG 则 env 为空，旧逻辑会导致 **authDebug 永远不输出**。
 */
const umiAuthDebugInject = ['0', 'false', 'off', 'no'].includes(
  String(process.env.UMI_APP_AUTH_DEBUG || '').trim().toLowerCase(),
)
  ? '0'
  : '1';

export default defineConfig({
  define: {
    'process.env.UMI_APP_ENV_LABEL': JSON.stringify(process.env.UMI_APP_ENV_LABEL || ''),
    /** 可选：部署了 Grafana 时写入完整 URL，工作台显示跳转（十五-24） */
    'process.env.UMI_APP_GRAFANA_URL': JSON.stringify(process.env.UMI_APP_GRAFANA_URL || ''),
    /** 非空时登录走独立 IAM；开发用 ``UMI_DEV_IAM_ORIGIN`` 反代 ``/iam-api``，生产用 nginx ``/iam-api`` → ``DEVAULT_CONSOLE_IAM_UPSTREAM`` */
    'process.env.UMI_APP_IAM_PREFIX': JSON.stringify(process.env.UMI_APP_IAM_PREFIX || ''),
    /** 仅 `'0'|'1'` 两值，见上 `umiAuthDebugInject`。 */
    'process.env.UMI_APP_AUTH_DEBUG': JSON.stringify(umiAuthDebugInject),
  },
  title: 'DeVault',
  locale: {
    default: 'en-US',
    antd: true,
    baseNavigator: false,
    useLocalStorage: true,
    title: false,
  },
  antd: {
    theme: {
      token: {
        colorPrimary: '#1677ff',
        borderRadius: 8,
      },
    },
  },
  access: {},
  model: {},
  initialState: {},
  request: {},
  layout: {
    locale: true,
    ...defaultSettings,
  },
  routes: [
    { path: '/user/login', layout: false, component: './user/login' },
    { path: '/user/integration', layout: false, component: './user/integration' },
    { path: '/user/reset-password', layout: false, component: './user/reset-password' },
    { path: '/user/accept-invite', layout: false, component: './user/accept-invite' },
    { path: '/user/change-password', layout: false, component: './user/change-password' },
    /**
     * 需登录的业务路由与根重定向并列在顶层（不再包一层无 `name` 的 `path: '/'`）。
     * 否则 ProLayout `clearMenuItem` 会丢掉该壳节点，侧栏 `menuData` 为空（mix 下无菜单）。
     * 会话守卫在 `app.tsx` 的 `layout.childrenRender`（`RequireSession`）；勿用 `wrappers`，以免 layout 插件扁平化破坏 mix 侧栏。
     */
    { path: '/', redirect: '/overview/welcome' },
    {
      path: '/overview',
      name: 'overview',
      icon: 'DashboardOutlined',
      routes: [
        {
          path: '/overview/welcome',
          name: 'welcome',
          icon: 'SmileOutlined',
          component: './welcome/index',
        },
        {
          path: '/overview/workbench',
          name: 'workbench',
          icon: 'HomeOutlined',
          component: './workbench/index',
        },
        {
          path: '/overview/team-invitations',
          name: 'team-invitations',
          icon: 'TeamOutlined',
          component: './overview/team-invitations',
          access: 'canInviteMembers',
        },
      ],
    },
    {
      path: '/backup',
      name: 'backup',
      icon: 'CloudSyncOutlined',
      routes: [
        {
          path: '/backup/jobs',
          name: 'jobs',
          icon: 'UnorderedListOutlined',
          component: './backup/jobs',
        },
        {
          path: '/backup/policies',
          name: 'policies',
          icon: 'FileTextOutlined',
          component: './backup/policies',
        },
        {
          path: '/backup/policies/new',
          name: 'new-policy',
          component: './backup/policies/edit',
          hideInMenu: true,
        },
        {
          path: '/backup/policies/:policyId',
          name: 'edit-policy',
          component: './backup/policies/EditRedirect',
          hideInMenu: true,
        },
        {
          path: '/backup/run',
          name: 'run',
          icon: 'PlayCircleOutlined',
          component: './backup/run',
        },
        {
          path: '/backup/precheck',
          name: 'precheck',
          icon: 'SearchOutlined',
          component: './backup/precheck',
        },
        {
          path: '/backup/artifacts',
          name: 'artifacts',
          icon: 'DatabaseOutlined',
          component: './backup/artifacts',
        },
      ],
    },
    {
      path: '/execution',
      name: 'execution',
      icon: 'ClusterOutlined',
      routes: [
        {
          path: '/execution/tenant-agents',
          name: 'tenant-agents',
          icon: 'TeamOutlined',
          component: './execution/tenant-agents',
        },
        {
          path: '/execution/agent-tokens',
          name: 'agent-tokens',
          icon: 'KeyOutlined',
          component: './execution/agent-tokens',
        },
        {
          path: '/execution/fleet',
          name: 'fleet',
          icon: 'CloudServerOutlined',
          component: './execution/fleet',
        },
        {
          path: '/execution/fleet/:agentId',
          name: 'fleet-agent-detail',
          component: './execution/fleet/detail',
          hideInMenu: true,
        },
      ],
    },
    {
      path: '/compliance',
      name: 'compliance',
      icon: 'SafetyOutlined',
      routes: [
        {
          path: '/compliance/schedules',
          name: 'schedules',
          icon: 'ScheduleOutlined',
          component: './compliance/schedules',
        },
        {
          path: '/compliance/restore-drill-schedules',
          name: 'restore-drill-schedules',
          icon: 'ExperimentOutlined',
          component: './compliance/restore-drill-schedules',
        },
      ],
    },
    {
      path: '/platform',
      name: 'platform',
      icon: 'SettingOutlined',
      access: 'canAdmin',
      routes: [
        {
          path: '/platform/tenants',
          name: 'tenants',
          icon: 'BankOutlined',
          component: './platform/tenants',
        },
        {
          path: '/platform/users/new',
          name: 'users-new',
          icon: 'UserAddOutlined',
          component: './platform/users-new',
        },
        {
          path: '/platform/users',
          name: 'users',
          icon: 'TeamOutlined',
          component: './platform/users',
        },
      ],
    },
  ],
  npmClient: 'npm',
  /**
   * 开发联调：与生产「同域反代」一致，将控制面根路径与 `/api` 指到同一后端（十五-08）。
   */
  proxy: {
    '/iam-api': {
      target: devIamOrigin,
      changeOrigin: true,
      pathRewrite: { '^/iam-api': '' },
    },
    '/api': { target: devApiOrigin, changeOrigin: true },
    '/openapi.json': { target: devApiOrigin, changeOrigin: true },
    '/docs': { target: devApiOrigin, changeOrigin: true },
    '/redoc': { target: devApiOrigin, changeOrigin: true },
    '/metrics': { target: devApiOrigin, changeOrigin: true },
    '/version': { target: devApiOrigin, changeOrigin: true },
    '/healthz': { target: devApiOrigin, changeOrigin: true },
  },
});
