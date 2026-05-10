import { LinkOutlined } from '@ant-design/icons';
import type { ProLayoutProps } from '@ant-design/pro-components';
import type { RequestConfig, RunTimeLayoutConfig } from '@umijs/max';
import { history, Link, request as maxRequest } from '@umijs/max';
import React from 'react';

import { Footer, RightContent } from '@/components';
import defaultSettings from '../config/defaultSettings';
import { STORAGE_BEARER_KEY, STORAGE_TENANT_ID_KEY } from '@/constants/storage';
import { openapiAuthSessionContract } from '@/openapi/contract';
import { errorConfig } from '@/requestErrorConfig';

const isDev = process.env.NODE_ENV === 'development';
const loginPath = '/user/login';
/** 未登录也可访问的认证相关页（含 §十六-11 邀请接受）。 */
const authPublicPaths = new Set([
  '/user/login',
  '/user/integration',
  '/user/register',
  '/user/reset-password',
  '/user/accept-invite',
]);

void openapiAuthSessionContract;

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
    } catch {
      const token = localStorage.getItem(STORAGE_BEARER_KEY);
      if (!token) return undefined;
      try {
        return await maxRequest<API.CurrentUser>('/api/v1/auth/session', {
          method: 'GET',
          skipErrorHandler: true,
          credentials: 'include',
          headers: { Authorization: `Bearer ${token}` },
        });
      } catch {
        localStorage.removeItem(STORAGE_BEARER_KEY);
        return undefined;
      }
    }
  };

  if (authPublicPaths.has(history.location.pathname)) {
    return {
      fetchUserInfo,
      settings: defaultSettings as Partial<ProLayoutProps>,
    };
  }

  const currentUser = await fetchUserInfo();
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
  onPageChange: () => {
    const { location } = history;
    if (!initialState?.currentUser && !authPublicPaths.has(location.pathname)) {
      history.replace(
        `${loginPath}?redirect=${encodeURIComponent(location.pathname + location.search + location.hash)}`,
      );
    }
  },
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
