import { LinkOutlined } from '@ant-design/icons';
import type { ProLayoutProps } from '@ant-design/pro-components';
import type { RequestConfig, RunTimeLayoutConfig } from '@umijs/max';
import { Link, request as maxRequest } from '@umijs/max';
import { App as AntdApp } from 'antd';
import React from 'react';

import { Footer, RightContent } from '@/components';
import defaultSettings from '../config/defaultSettings';
import { STORAGE_BEARER_KEY, STORAGE_TENANT_ID_KEY } from '@/constants/storage';
import { openapiAuthSessionContract } from '@/openapi/contract';
import { errorConfig } from '@/requestErrorConfig';
import { authDebug } from '@/utils/auth-debug';

const isDev = process.env.NODE_ENV === 'development';

void openapiAuthSessionContract;

/** Ant Design 5：`App.useApp()` 的 message/modal 等依赖此包裹，否则部分页成功提示不显示。 */
export function rootContainer(container: React.ReactNode) {
  return <AntdApp>{container}</AntdApp>;
}

async function ensureTenantSelection(user: API.CurrentUser): Promise<void> {
  try {
    const rows = await maxRequest<API.TenantRow[]>('/api/v1/tenants', { skipErrorHandler: true });
    const allow = user.allowed_tenant_ids;
    const visible =
      allow === null ? rows : rows.filter((t: API.TenantRow) => allow.includes(t.id));
    if (!visible.length) return;
    const cur = localStorage.getItem(STORAGE_TENANT_ID_KEY);
    const ok = cur && visible.some((t: API.TenantRow) => t.id === cur);
    if (!ok) localStorage.setItem(STORAGE_TENANT_ID_KEY, visible[0].id);
  } catch {
    /* ignore */
  }
}

export async function getInitialState(): Promise<{
  settings?: Partial<ProLayoutProps>;
  currentUser?: API.CurrentUser;
  canAdmin?: boolean;
  canWrite?: boolean;
  canInviteMembers?: boolean;
  fetchUserInfo?: () => Promise<API.CurrentUser | undefined>;
}> {
  const fetchUserInfo = async () => {
    try {
      return await maxRequest<API.CurrentUser>('/api/v1/auth/session', {
        method: 'GET',
        skipErrorHandler: true,
        credentials: 'include',
      });
    } catch (e) {
      const status = (e as { response?: { status?: number } })?.response?.status;
      authDebug('getInitialState:sessionRequestFailed', {
        httpStatus: status ?? 'unknown',
        hadBearer: typeof window !== 'undefined' && Boolean(localStorage.getItem(STORAGE_BEARER_KEY)),
      });
      localStorage.removeItem(STORAGE_BEARER_KEY);
      return undefined;
    }
  };

  /**
   * 所有入口路径统一解析会话（含登录等白名单页），避免「白名单短路」与 ProLayout
   * 闭包中的 `currentUser` 长期不一致；未登录时 `fetchUserInfo` 返回 undefined。
   */
  authDebug('getInitialState:start', {
    pathname: typeof window !== 'undefined' ? window.location.pathname : '(no-window)',
    hasBearer: typeof window !== 'undefined' && Boolean(localStorage.getItem(STORAGE_BEARER_KEY)),
  });
  const currentUser = await fetchUserInfo();
  authDebug('getInitialState:afterSession', {
    hasCurrentUser: Boolean(currentUser),
    principal: currentUser?.principal_label,
    needsMfa: currentUser?.needs_mfa,
  });
  const gated = Boolean(currentUser?.needs_mfa);
  const canAdmin = Boolean(currentUser && !gated && currentUser.role === 'admin');
  const canWrite = Boolean(
    currentUser && !gated && (currentUser.role === 'admin' || currentUser.role === 'operator'),
  );
  const canInviteMembers = Boolean(
    currentUser &&
      !gated &&
      currentUser.tenants?.some((t) => t.membership_role === 'tenant_admin'),
  );

  if (currentUser) {
    await ensureTenantSelection(currentUser);
  }

  return {
    fetchUserInfo,
    currentUser,
    canAdmin,
    canWrite,
    canInviteMembers,
    settings: defaultSettings as Partial<ProLayoutProps>,
  };
}

export const layout: RunTimeLayoutConfig = ({ initialState }) => ({
  menuItemRender: (menuItemProps, defaultDom) => {
    if (menuItemProps.isUrl || !menuItemProps.path || menuItemProps.children?.length) {
      return defaultDom;
    }
    return <Link to={menuItemProps.path}>{defaultDom}</Link>;
  },
  actionsRender: () => [<RightContent key="right-content" />],
  footerRender: () => <Footer />,
  links: isDev
    ? [
        <a key="openapi" href="/docs" target="_blank" rel="noreferrer">
          <LinkOutlined />
          <span style={{ marginLeft: 8 }}>OpenAPI</span>
        </a>,
      ]
    : [],
  /** 精简：不使用官方模板中的 `bgLayoutImgList` 与 `SettingDrawer`。 */
  ...initialState?.settings,
});

export const request: RequestConfig = {
  ...errorConfig,
  credentials: 'include',
};
