import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  docsSidebar: [
    {
      type: 'category',
      label: '入门',
      collapsed: false,
      items: [
        'intro/index',
        'intro/quickstart',
        'intro/architecture-overview',
        'intro/roadmap',
      ],
    },
    {
      type: 'category',
      label: '安装与运行',
      collapsed: false,
      items: [
        'install/requirements',
        'install/docker-compose',
        'install/database-migrations',
        'install/control-plane-database-dr',
        'install/grpc-multi-instance',
        'install/configuration',
        'install/observability',
      ],
    },
    {
      type: 'category',
      label: '网络与安全',
      collapsed: false,
      items: [
        'security/agent-connectivity',
        'security/tls-and-gateway',
        'security/api-access',
        'security/artifact-encryption',
      ],
    },
    {
      type: 'category',
      label: '存储与数据面',
      collapsed: false,
      items: [
        'storage/object-store-model',
        'storage/sts-assume-role',
        'storage/large-objects',
        'storage/tuning',
      ],
    },
    {
      type: 'category',
      label: '使用指南',
      collapsed: false,
      items: [
        'guides/backup-and-restore',
        'guides/restore-drill',
        'guides/policies-and-schedules',
        'guides/retention-lifecycle',
        'guides/web-console',
      ],
    },
    {
      type: 'category',
      label: '参考',
      collapsed: false,
      items: [
        'reference/http-api',
        'reference/grpc-services',
        'reference/ports-and-paths',
        'reference/tenants',
        'reference/agent-fleet',
        'reference/access-control',
      ],
    },
    {
      type: 'category',
      label: '开发与贡献',
      collapsed: false,
      items: [
        'development/local-setup',
        'development/project-structure',
        'development/testing',
        'development/releasing',
        'development/compatibility',
      ],
    },
  ],
};

export default sidebars;
