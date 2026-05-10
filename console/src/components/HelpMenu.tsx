import { DownOutlined } from '@ant-design/icons';
import type { MenuProps } from 'antd';
import { Dropdown } from 'antd';
import React from 'react';

function openPath(path: string) {
  window.open(path, '_blank', 'noopener,noreferrer');
}

const items: MenuProps['items'] = [
  { key: 'docs', label: 'API 文档 /docs', onClick: () => openPath('/docs') },
  { key: 'metrics', label: '指标 /metrics', onClick: () => openPath('/metrics') },
  { key: 'version', label: '版本 JSON /version', onClick: () => openPath('/version') },
  { key: 'healthz', label: '健康检查 /healthz', onClick: () => openPath('/healthz') },
];

/**
 * 顶栏帮助入口（十五-09）：新窗口打开控制面诊断与文档路径。
 */
const HelpMenu: React.FC = () => (
  <Dropdown menu={{ items }} trigger={['click']}>
    <span className="ant-pro-global-header-index-action" style={{ paddingInline: 8 }}>
      <a onClick={(e) => e.preventDefault()}>
        帮助 <DownOutlined />
      </a>
    </span>
  </Dropdown>
);

export default HelpMenu;
