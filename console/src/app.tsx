import { LinkOutlined } from '@ant-design/icons';
import type { MenuDataItem } from '@ant-design/pro-layout';
import type { ProLayoutProps } from '@ant-design/pro-components';
import type { RequestConfig, RunTimeLayoutConfig } from '@umijs/max';
import { Link, request as maxRequest } from '@umijs/max';
import { App as AntdApp } from 'antd';
import React from 'react';

import { Footer, RightContent } from '@/components';
import defaultSettings from '../config/defaultSettings';
import { STORAGE_BEARER_KEY } from '@/constants/storage';
import RequireSession from '@/wrappers/require-session';
import { ensureTenantSelection } from '@/utils/ensure-tenant-selection';
import { openapiAuthSessionContract } from '@/openapi/contract';
import { errorConfig } from '@/requestErrorConfig';
import { authDebug, authDebugBootProbe } from '@/utils/auth-debug';
import {
  isLayoutDebugEnabled,
  layoutDebug,
  layoutDebugBootProbe,
  summarizeMenuData,
} from '@/utils/layout-debug';

const isDev = process.env.NODE_ENV === 'development';

/** Umi `RunTimeLayoutConfig` 对 `rightContentRender` 的签名与 Pro `Partial<ProLayoutProps>` 不一致，勿从 settings 透传。 */
function settingsForUmiLayout(settings: Partial<ProLayoutProps> | undefined) {
  if (!settings) return {};
  const { rightContentRender: _ignored, ...rest } = settings;
  void _ignored;
  return rest;
}

let layoutConfigInvokeSeq = 0;
let menuDataRenderLogCount = 0;
let postMenuDataLogCount = 0;
let childrenRenderLogCount = 0;
const LAYOUT_LOG_CAP = 25;

void openapiAuthSessionContract;

/** Ant Design 5：`App.useApp()` 的 message/modal 等依赖此包裹，否则部分页成功提示不显示。 */
export function rootContainer(container: React.ReactNode) {
  authDebugBootProbe('rootContainer', {});
  layoutDebugBootProbe({});
  return <AntdApp>{container}</AntdApp>;
}

export async function getInitialState(): Promise<{
  settings?: Partial<ProLayoutProps>;
  currentUser?: API.CurrentUser;
  canAdmin?: boolean;
  canWrite?: boolean;
  canInviteMembers?: boolean;
  fetchUserInfo?: () => Promise<API.CurrentUser | undefined>;
}> {
  authDebugBootProbe('getInitialState:entry', {
    pathname: typeof window !== 'undefined' ? window.location.pathname : '(ssr)',
    hasBearer: typeof window !== 'undefined' && Boolean(localStorage.getItem(STORAGE_BEARER_KEY)),
  });

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

export const layout: RunTimeLayoutConfig = (initData) => {
  const { initialState, loading } = initData;
  layoutConfigInvokeSeq += 1;
  if (layoutConfigInvokeSeq <= LAYOUT_LOG_CAP || layoutConfigInvokeSeq % 40 === 0) {
    layoutDebug('layout:runtimeConfigInvoked', {
      seq: layoutConfigInvokeSeq,
      initialStateLoading: loading,
      hasCurrentUser: Boolean(initialState?.currentUser),
      settingsLayout: initialState?.settings?.layout,
      settingsNavTheme: initialState?.settings?.navTheme,
    });
  }

  return {
    /** 与路由 `wrappers` 等价，但避免 layout 插件对 `isWrapper` 扁平化时弄乱传给 ProLayout 的 `route`（mix 侧栏为空）。 */
    childrenRender: (children, layoutProps) => {
      if (isLayoutDebugEnabled() && childrenRenderLogCount < LAYOUT_LOG_CAP) {
        childrenRenderLogCount += 1;
        const keys =
          layoutProps && typeof layoutProps === 'object'
            ? Object.keys(layoutProps as Record<string, unknown>)
            : [];
        // Umi 传入的是 Layout 外层 props；菜单数据以 menuDataRender / postMenuData 日志为准。
        layoutDebug('layout:childrenRender', {
          call: childrenRenderLogCount,
          outerPropKeys: keys.slice(0, 24),
        });
      }
      return <RequireSession>{children}</RequireSession>;
    },
    menuDataRender: (menuData) => {
      if (isLayoutDebugEnabled() && menuDataRenderLogCount < LAYOUT_LOG_CAP) {
        menuDataRenderLogCount += 1;
        layoutDebug('layout:menuDataRender', {
          call: menuDataRenderLogCount,
          topLevelCount: menuData.length,
          tree: summarizeMenuData(menuData),
        });
      }
      return menuData;
    },
    postMenuData: (menusData) => {
      if (isLayoutDebugEnabled() && postMenuDataLogCount < LAYOUT_LOG_CAP) {
        postMenuDataLogCount += 1;
        layoutDebug('layout:postMenuData', {
          call: postMenuDataLogCount,
          count: menusData?.length ?? 0,
          tree: menusData?.length ? summarizeMenuData(menusData) : [],
        });
      }
      // 勿 `menusData ?? []`：传入 `undefined` 时不应变成空数组，否则会误清空侧栏。
      return menusData as MenuDataItem[];
    },
    onPageChange: (loc) => {
      layoutDebug('layout:onPageChange', { pathname: loc?.pathname });
    },
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
    ...settingsForUmiLayout(initialState?.settings),
  };
};

export const request: RequestConfig = {
  ...errorConfig,
  credentials: 'include',
};
