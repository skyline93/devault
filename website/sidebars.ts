import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

/** 各角色侧栏：首组默认展开，其余分组默认折叠，便于抓住阅读重点。 */
const sidebars: SidebarsConfig = {
  productSidebar: [
    {
      type: 'category',
      label: '开始',
      collapsed: false,
      items: [
        {type: 'link', label: '文档首页', href: '/docs/'},
        'product/overview',
        'product/deployment-models',
      ],
    },
    {
      type: 'category',
      label: '架构与路线',
      collapsed: true,
      items: ['product/architecture', 'product/roadmap'],
    },
  ],
  userSidebar: [
    {
      type: 'category',
      label: '导读与入门',
      collapsed: false,
      items: [
        {type: 'link', label: '文档首页', href: '/docs/'},
        'user/index',
        'user/concepts',
        'user/quickstart',
      ],
    },
    {
      type: 'category',
      label: '备份、策略与保留',
      collapsed: true,
      items: [
        'user/backup-and-restore',
        'user/policies-and-schedules',
        'user/retention-lifecycle',
        'user/restore-drill',
      ],
    },
    {
      type: 'category',
      label: 'Web 控制台',
      collapsed: true,
      items: ['user/web-console'],
    },
  ],
  adminSidebar: [
    {
      type: 'category',
      label: '导读与治理',
      collapsed: false,
      items: [
        {type: 'link', label: '文档首页', href: '/docs/'},
        'admin/index',
        'admin/tenants-and-rbac',
        'admin/agent-fleet',
        'admin/agent-credential-lifecycle',
        'admin/agent-pools',
      ],
    },
    {
      type: 'category',
      label: '安装与环境',
      collapsed: true,
      items: [
        'admin/requirements',
        'admin/docker-compose',
        'admin/kubernetes-helm',
        'admin/database-migrations',
        'admin/configuration',
      ],
    },
    {
      type: 'category',
      label: '规模与网络拓扑',
      collapsed: true,
      items: [
        'admin/grpc-multi-instance',
        'admin/enterprise-reference-architecture',
      ],
    },
    {
      type: 'category',
      label: '可靠性与观测',
      collapsed: true,
      items: ['admin/control-plane-database-dr', 'admin/observability'],
    },
    {
      type: 'category',
      label: '存储与数据面',
      collapsed: true,
      items: [
        'storage/object-store-model',
        'storage/sts-assume-role',
        'storage/large-objects',
        'storage/tuning',
      ],
    },
  ],
  trustSidebar: [
    {
      type: 'category',
      label: '导读与概览',
      collapsed: false,
      items: [
        {type: 'link', label: '文档首页', href: '/docs/'},
        'trust/index',
        'trust/whitepaper',
      ],
    },
    {
      type: 'category',
      label: '网络与入口',
      collapsed: true,
      items: ['trust/agent-connectivity', 'trust/tls-and-gateway'],
    },
    {
      type: 'category',
      label: '访问与数据保护',
      collapsed: true,
      items: ['trust/api-access', 'trust/artifact-encryption'],
    },
  ],
  referenceSidebar: [
    {
      type: 'category',
      label: 'API',
      collapsed: false,
      items: [
        {type: 'link', label: '文档首页', href: '/docs/'},
        'reference/http-api',
        'reference/grpc-services',
      ],
    },
    {
      type: 'category',
      label: '部署速查',
      collapsed: true,
      items: ['reference/ports-and-paths'],
    },
  ],
  engineeringSidebar: [
    {
      type: 'category',
      label: '导读与环境',
      collapsed: false,
      items: [
        {type: 'link', label: '文档首页', href: '/docs/'},
        'engineering/index',
        'engineering/local-setup',
        'engineering/project-structure',
      ],
    },
    {
      type: 'category',
      label: '架构与契约',
      collapsed: true,
      items: [
        'engineering/platform-architecture',
        'engineering/control-plane-database-er',
        'engineering/compatibility',
      ],
    },
    {
      type: 'category',
      label: '测试与发布',
      collapsed: true,
      items: ['engineering/testing', 'engineering/releasing'],
    },
    {
      type: 'category',
      label: '交付节奏与批量引导',
      collapsed: true,
      items: ['guides/web-console', 'guides/iac-bootstrap'],
    },
  ],
};

export default sidebars;
