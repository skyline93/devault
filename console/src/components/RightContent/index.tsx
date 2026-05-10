import { Space, Tag } from 'antd';
import React from 'react';

import AvatarDropdown from '@/components/AvatarDropdown';
import HelpMenu from '@/components/HelpMenu';
import TenantSwitcher from '@/components/TenantSwitcher';

/**
 * 顶栏右侧操作区（对齐 Ant Design Pro `RightContent` 组合方式）。
 */
const RightContent: React.FC = () => {
  const envLabel = process.env.UMI_APP_ENV_LABEL?.trim() || process.env.NODE_ENV;
  return (
    <Space size={0} align="center" style={{ marginRight: 8 }}>
      <Tag color="processing" style={{ marginRight: 4 }}>
        {envLabel}
      </Tag>
      <HelpMenu />
      <TenantSwitcher />
      <AvatarDropdown />
    </Space>
  );
};

export default RightContent;
