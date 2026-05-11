import { DownOutlined } from '@ant-design/icons';
import type { MenuProps } from 'antd';
import { Dropdown } from 'antd';
import React, { useMemo } from 'react';
import { useIntl } from '@umijs/max';

function openPath(path: string) {
  window.open(path, '_blank', 'noopener,noreferrer');
}

const HelpMenu: React.FC = () => {
  const { formatMessage } = useIntl();
  const items: MenuProps['items'] = useMemo(
    () => [
      {
        key: 'docs',
        label: formatMessage({ id: 'component.helpDocsApi' }),
        onClick: () => openPath('/docs'),
      },
      {
        key: 'metrics',
        label: formatMessage({ id: 'component.helpMetrics' }),
        onClick: () => openPath('/metrics'),
      },
      {
        key: 'version',
        label: formatMessage({ id: 'component.helpVersion' }),
        onClick: () => openPath('/version'),
      },
      {
        key: 'healthz',
        label: formatMessage({ id: 'component.helpHealth' }),
        onClick: () => openPath('/healthz'),
      },
    ],
    [formatMessage],
  );

  return (
    <Dropdown menu={{ items }} trigger={['click']}>
      <span className="ant-pro-global-header-index-action" style={{ paddingInline: 8 }}>
        <a onClick={(e) => e.preventDefault()}>
          {formatMessage({ id: 'component.help' })} <DownOutlined />
        </a>
      </span>
    </Dropdown>
  );
};

export default HelpMenu;
