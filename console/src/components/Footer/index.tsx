import { DefaultFooter } from '@ant-design/pro-components';
import { GithubOutlined } from '@ant-design/icons';
import React from 'react';

/**
 * 与 Pro 模板一致的页脚（精简链接）。
 */
const Footer: React.FC = () => (
  <DefaultFooter
    copyright={`${new Date().getFullYear()} DeVault`}
    links={[
      {
        key: 'docs',
        title: '控制面 OpenAPI',
        href: '/docs',
        blankTarget: true,
      },
      {
        key: 'github',
        title: <GithubOutlined />,
        href: 'https://github.com/skyline93/devault',
        blankTarget: true,
      },
    ]}
  />
);

export default Footer;
