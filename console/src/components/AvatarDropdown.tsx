import { LogoutOutlined, UserOutlined } from '@ant-design/icons';
import { history, useModel } from '@umijs/max';
import { Avatar, Dropdown, Space, Typography } from 'antd';
import type { MenuProps } from 'antd';
import React from 'react';

import HeaderDropdown from '@/components/HeaderDropdown';
import { STORAGE_BEARER_KEY, STORAGE_TENANT_ID_KEY } from '@/constants/storage';

const loginPath = '/user/login';

/**
 * 与 Pro 模板 `AvatarDropdown` 同构：头像 + 下拉菜单（账户信息 / 退出）。
 */
const AvatarDropdown: React.FC = () => {
  const { initialState, setInitialState } = useModel('@@initialState');
  const user = initialState?.currentUser;
  if (!user) return null;

  const onLogout = () => {
    void fetch('/api/v1/auth/logout', { method: 'POST', credentials: 'include' }).catch(() => {});
    localStorage.removeItem(STORAGE_BEARER_KEY);
    localStorage.removeItem(STORAGE_TENANT_ID_KEY);
    setInitialState((s) => ({
      ...s,
      currentUser: undefined,
      canAdmin: false,
      canWrite: false,
    }));
    history.push(loginPath);
  };

  const items: MenuProps['items'] = [
    {
      key: 'info',
      disabled: true,
      label: (
        <div style={{ maxWidth: 240 }}>
          <Typography.Text strong>{user.principal_label}</Typography.Text>
          <div>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              角色：{user.role}
            </Typography.Text>
          </div>
        </div>
      ),
    },
    { type: 'divider' },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      onClick: onLogout,
    },
  ];

  return (
    <HeaderDropdown menu={{ items }}>
      <span className="ant-pro-global-header-index-action" style={{ cursor: 'pointer', display: 'inline-flex' }}>
        <Space size={8}>
          <Avatar size="small" icon={<UserOutlined />} style={{ backgroundColor: '#1890ff' }} />
          <span style={{ maxWidth: 140, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {user.principal_label}
          </span>
        </Space>
      </span>
    </HeaderDropdown>
  );
};

export default AvatarDropdown;
