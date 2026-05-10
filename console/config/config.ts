import { defineConfig } from '@umijs/max';
import zhCN from 'antd/locale/zh_CN';

import defaultSettings from './defaultSettings';

/** Dev-only: Umi ``proxy`` targets (``npm run dev``). Production uses nginx ``console-spa.conf.template``. */
const devApiOrigin = (process.env.UMI_DEV_API_ORIGIN || 'http://127.0.0.1:8000').replace(/\/$/, '');
const devIamOrigin = (process.env.UMI_DEV_IAM_ORIGIN || 'http://127.0.0.1:8100').replace(/\/$/, '');

export default defineConfig({
  define: {
    'process.env.UMI_APP_ENV_LABEL': JSON.stringify(process.env.UMI_APP_ENV_LABEL || ''),
    /** 可选：部署了 Grafana 时写入完整 URL，工作台显示跳转（十五-24） */
    'process.env.UMI_APP_GRAFANA_URL': JSON.stringify(process.env.UMI_APP_GRAFANA_URL || ''),
    /** 非空时登录/注册走独立 IAM；开发用 ``UMI_DEV_IAM_ORIGIN`` 反代 ``/iam-api``，生产用 nginx ``/iam-api`` → ``DEVAULT_CONSOLE_IAM_UPSTREAM`` */
    'process.env.UMI_APP_IAM_PREFIX': JSON.stringify(process.env.UMI_APP_IAM_PREFIX || ''),
  },
  title: 'DeVault',
  antd: {
    configProvider: {
      locale: zhCN,
    },
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
    locale: false,
    ...defaultSettings,
  },
  routes: [
    { path: '/user/login', layout: false, component: './user/login' },
    { path: '/user/integration', layout: false, component: './user/integration' },
    { path: '/user/register', layout: false, component: './user/register' },
    { path: '/user/reset-password', layout: false, component: './user/reset-password' },
    { path: '/user/accept-invite', layout: false, component: './user/accept-invite' },
    { path: '/', redirect: '/overview/welcome' },
    {
      path: '/overview',
      name: '概览',
      icon: 'DashboardOutlined',
      routes: [
        {
          path: '/overview/welcome',
          name: '欢迎',
          icon: 'SmileOutlined',
          component: './welcome/index',
        },
        {
          path: '/overview/workbench',
          name: '工作台',
          icon: 'HomeOutlined',
          component: './workbench/index',
        },
        {
          path: '/overview/team-invitations',
          name: '成员邀请',
          icon: 'TeamOutlined',
          component: './overview/team-invitations',
          access: 'canInviteMembers',
        },
      ],
    },
    {
      path: '/backup',
      name: '备份与恢复',
      icon: 'CloudSyncOutlined',
      routes: [
        {
          path: '/backup/jobs',
          name: '作业中心',
          icon: 'UnorderedListOutlined',
          component: './backup/jobs',
        },
        {
          path: '/backup/policies',
          name: '策略',
          icon: 'FileTextOutlined',
          component: './backup/policies',
        },
        {
          path: '/backup/policies/new',
          name: '新建策略',
          component: './backup/policies/edit',
          hideInMenu: true,
        },
        {
          path: '/backup/policies/:policyId',
          name: '编辑策略',
          component: './backup/policies/edit',
          hideInMenu: true,
        },
        {
          path: '/backup/run',
          name: '发起备份',
          icon: 'PlayCircleOutlined',
          component: './backup/run',
        },
        {
          path: '/backup/precheck',
          name: '路径预检',
          icon: 'SearchOutlined',
          component: './backup/precheck',
        },
        {
          path: '/backup/artifacts',
          name: '制品',
          icon: 'DatabaseOutlined',
          component: './backup/artifacts',
        },
      ],
    },
    {
      path: '/execution',
      name: '执行面',
      icon: 'ClusterOutlined',
      routes: [
        {
          path: '/execution/tenant-agents',
          name: '租户内 Agents',
          icon: 'TeamOutlined',
          component: './execution/tenant-agents',
        },
        {
          path: '/execution/agent-pools',
          name: 'Agent 池',
          icon: 'ApartmentOutlined',
          component: './execution/agent-pools',
        },
        {
          path: '/execution/agent-pools/:poolId',
          name: '池详情',
          component: './execution/agent-pools/detail',
          hideInMenu: true,
        },
        {
          path: '/execution/fleet',
          name: '全舰队',
          icon: 'CloudServerOutlined',
          component: './execution/fleet',
        },
        {
          path: '/execution/fleet/:agentId',
          name: 'Agent 详情',
          component: './execution/fleet/detail',
          hideInMenu: true,
        },
      ],
    },
    {
      path: '/compliance',
      name: '合规与演练',
      icon: 'SafetyOutlined',
      routes: [
        {
          path: '/compliance/schedules',
          name: '备份计划',
          icon: 'ScheduleOutlined',
          component: './compliance/schedules',
        },
        {
          path: '/compliance/restore-drill-schedules',
          name: '恢复演练计划',
          icon: 'ExperimentOutlined',
          component: './compliance/restore-drill-schedules',
        },
      ],
    },
    {
      path: '/platform',
      name: '平台管理',
      icon: 'SettingOutlined',
      access: 'canAdmin',
      routes: [
        {
          path: '/platform/tenants',
          name: '租户',
          icon: 'BankOutlined',
          component: './platform/tenants',
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
