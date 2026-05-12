import { LogoutOutlined, UserOutlined } from '@ant-design/icons';
import { history, useIntl, useModel } from '@umijs/max';
import { Avatar, Dropdown, Space, Tag, Typography } from 'antd';
import type { MenuProps } from 'antd';
import React, { useMemo } from 'react';

import HeaderDropdown from '@/components/HeaderDropdown';
import { LOGIN_PATH } from '@/constants/auth-routes';
import { STORAGE_BEARER_KEY, STORAGE_IAM_PWD_CHANGE_REQUIRED, STORAGE_REFRESH_TOKEN_KEY, STORAGE_TENANT_ID_KEY } from '@/constants/storage';
import { computeSessionAccessFlags } from '@/utils/auth-access';

/**
 * 与 Pro 模板 `AvatarDropdown` 同构：头像 + 下拉菜单（账户信息 / 退出）。
 */
const AvatarDropdown: React.FC = () => {
  const { formatMessage } = useIntl();
  const { initialState, setInitialState } = useModel('@@initialState');
  const user = initialState?.currentUser;

  const primaryLabel = useMemo(() => {
    if (!user) return '';
    const dn = (user.display_name || '').trim();
    if (dn) return dn;
    const em = (user.email || '').trim();
    if (em) return em;
    return user.principal_label;
  }, [user]);

  const currentTenantLabel = useMemo(() => {
    if (!user?.tenants?.length) return null;
    const tid = typeof window !== 'undefined' ? localStorage.getItem(STORAGE_TENANT_ID_KEY) : null;
    if (!tid) return null;
    const row = user.tenants.find((t) => t.tenant_id === tid);
    if (!row) return tid;
    return `${row.name}（${row.slug}）`;
  }, [user]);

  const permList = useMemo(() => user?.permissions?.filter(Boolean) ?? [], [user?.permissions]);

  if (!user) return null;

  const onLogout = () => {
    void fetch('/api/v1/auth/logout', { method: 'POST', credentials: 'include' }).catch(() => {});
    localStorage.removeItem(STORAGE_BEARER_KEY);
    localStorage.removeItem(STORAGE_REFRESH_TOKEN_KEY);
    localStorage.removeItem(STORAGE_IAM_PWD_CHANGE_REQUIRED);
    localStorage.removeItem(STORAGE_TENANT_ID_KEY);
    setInitialState((s) => ({
      ...s,
      currentUser: undefined,
      canAdmin: false,
      canWrite: false,
      canInviteMembers: false,
      needsPasswordChange: false,
    }));
    history.push(LOGIN_PATH);
  };

  const items: MenuProps['items'] = [
    {
      key: 'info',
      disabled: true,
      label: (
        <div style={{ maxWidth: 280 }}>
          <Typography.Text strong>{primaryLabel}</Typography.Text>
          {primaryLabel !== user.principal_label ? (
            <div>
              <Typography.Text type="secondary" style={{ fontSize: 11 }} copyable>
                {user.principal_label}
              </Typography.Text>
            </div>
          ) : null}
          <div>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              {formatMessage({ id: 'component.role' })}：{user.role}
            </Typography.Text>
          </div>
          {currentTenantLabel ? (
            <div>
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                {formatMessage({ id: 'component.currentOrg' })}：{currentTenantLabel}
              </Typography.Text>
            </div>
          ) : null}
          {permList.length > 0 ? (
            <div style={{ marginTop: 6 }}>
              <Typography.Text type="secondary" style={{ fontSize: 11, display: 'block', marginBottom: 4 }}>
                {formatMessage({ id: 'component.grantedPermissions' })}
              </Typography.Text>
              <div style={{ maxHeight: 160, overflowY: 'auto' }}>
                {permList.map((p) => (
                  <Tag key={p} style={{ marginBottom: 4, fontSize: 11 }}>
                    {p}
                  </Tag>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      ),
    },
    { type: 'divider' },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: formatMessage({ id: 'component.logout' }),
      onClick: onLogout,
    },
  ];

  return (
    <HeaderDropdown menu={{ items }}>
      <span className="ant-pro-global-header-index-action" style={{ cursor: 'pointer', display: 'inline-flex' }}>
        <Space size={8}>
          <Avatar size="small" icon={<UserOutlined />} style={{ backgroundColor: '#1890ff' }} />
          <span style={{ maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {primaryLabel}
          </span>
        </Space>
      </span>
    </HeaderDropdown>
  );
};

export default AvatarDropdown;
