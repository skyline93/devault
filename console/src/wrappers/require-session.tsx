import { history, useModel } from '@umijs/max';
import { Spin } from 'antd';
import React, { useEffect, useMemo } from 'react';

import { LOGIN_PATH } from '@/constants/auth-routes';
import { authDebug } from '@/utils/auth-debug';

/**
 * 受保护业务路由外层守卫：用 `@@initialState` 作为单一事实来源，避免 ProLayout
 * `onPageChange` 捕获陈旧 `initialState` 导致「登录成功立刻被 replace 回登录页」。
 */
export default function RequireSession(props: { children: React.ReactNode }) {
  const { initialState, loading } = useModel('@@initialState');
  const redirectHref = useMemo(() => {
    if (typeof window === 'undefined') return '';
    const { pathname, search, hash } = window.location;
    return `${LOGIN_PATH}?redirect=${encodeURIComponent(pathname + search + hash)}`;
  }, []);

  useEffect(() => {
    authDebug('requireSession:effect', {
      loading,
      hasCurrentUser: Boolean(initialState?.currentUser),
      pathname: typeof window !== 'undefined' ? window.location.pathname : '',
    });
    if (loading) return;
    if (!initialState?.currentUser) {
      authDebug('requireSession:replaceToLogin', { redirectHref });
      history.replace(redirectHref);
    }
  }, [loading, initialState?.currentUser, redirectHref]);

  if (loading) {
    return (
      <div
        style={{
          display: 'flex',
          minHeight: '50vh',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Spin size="large" />
      </div>
    );
  }

  if (!initialState?.currentUser) {
    return (
      <div
        style={{
          display: 'flex',
          minHeight: '50vh',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Spin size="large" />
      </div>
    );
  }

  return <>{props.children}</>;
}
