import { DefaultFooter } from '@ant-design/pro-components';
import { GithubOutlined } from '@ant-design/icons';
import React from 'react';
import { useIntl } from '@umijs/max';

const Footer: React.FC = () => {
  const { formatMessage } = useIntl();
  return (
    <DefaultFooter
      copyright={`${new Date().getFullYear()} DeVault`}
      links={[
        {
          key: 'docs',
          title: formatMessage({ id: 'component.footerOpenapi' }),
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
};

export default Footer;
