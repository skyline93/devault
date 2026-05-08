import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const GITEE_ORG = 'greene93';
const GITEE_REPO = 'devault';
const DEFAULT_BRANCH = 'dev';
const GITEE_REPO_URL = `https://gitee.com/${GITEE_ORG}/${GITEE_REPO}`;

const config: Config = {
  title: 'DeVault',
  tagline: '开发者向备份与恢复平台',
  favicon: 'img/favicon.ico',

  markdown: {
    mermaid: true,
  },
  themes: ['@docusaurus/theme-mermaid'],

  future: {
    v4: true,
  },

  url: 'https://your-docs.example.com',
  baseUrl: '/',

  organizationName: GITEE_ORG,
  projectName: GITEE_REPO,

  onBrokenLinks: 'throw',

  i18n: {
    defaultLocale: 'zh-Hans',
    locales: ['zh-Hans'],
    localeConfigs: {
      'zh-Hans': {
        label: '简体中文',
        htmlLang: 'zh-Hans',
      },
    },
  },

  presets: [
    [
      'classic',
      {
        docs: {
          routeBasePath: '/docs',
          path: 'docs',
          sidebarPath: './sidebars.ts',
          editUrl: `${GITEE_REPO_URL}/tree/${DEFAULT_BRANCH}/website/`,
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    image: 'img/docusaurus-social-card.jpg',
    colorMode: {
      respectPrefersColorScheme: true,
    },
    navbar: {
      title: 'DeVault',
      logo: {
        alt: 'DeVault',
        src: 'img/logo.svg',
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'docsSidebar',
          position: 'left',
          label: '文档',
        },
        {
          href: GITEE_REPO_URL,
          label: '源码',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: '文档',
          items: [
            {
              label: '从这里开始',
              to: '/docs/intro/',
            },
            {
              label: '快速开始',
              to: '/docs/intro/quickstart',
            },
          ],
        },
        {
          title: '仓库',
          items: [
            {
              label: 'Gitee',
              href: GITEE_REPO_URL,
            },
            {
              label: '变更记录',
              href: `${GITEE_REPO_URL}/blob/${DEFAULT_BRANCH}/CHANGELOG.md`,
            },
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} DeVault。使用 Docusaurus 构建。`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['bash', 'json', 'http', 'nginx'],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
