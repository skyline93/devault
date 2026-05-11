import { history, request, useModel } from '@umijs/max';
import { Spin } from 'antd';
import React, { useEffect, useMemo, useRef } from 'react';

import { LOGIN_PATH } from '@/constants/auth-routes';
import { STORAGE_BEARER_KEY } from '@/constants/storage';
import { authDebug } from '@/utils/auth-debug';
import { ensureTenantSelection } from '@/utils/ensure-tenant-selection';

/**
 * 受保护业务路由外层守卫：用 `@@initialState` 作为单一事实来源。
 *
 * 若本地已有 Bearer 但模型尚未带上 `currentUser`（登录后 `setInitialState` 与路由切换竞态），
 * 先静默拉取一次 `/api/v1/auth/session` 并写回 `@@initialState`，避免误 `replace` 回登录页。
 */
export default function RequireSession(props: { children: React.ReactNode }) {
  const { initialState, loading, setInitialState } = useModel('@@initialState');
  const redirectHref = useMemo(() => {
    if (typeof window === 'undefined') return '';
    const { pathname, search, hash } = window.location;
    return `${LOGIN_PATH}?redirect=${encodeURIComponent(pathname + search + hash)}`;
  }, []);

  const bearerHydrateStarted = useRef(false);
  const silentInFlight = useRef(false);
  /** 静默 `setInitialState` 已调用，等待 `@@initialState` 提交；此期间禁止误 replace。 */
  const awaitingModelAfterSilentHydrate = useRef(false);

  useEffect(() => {
    authDebug('requireSession:effect', {
      loading,
      hasCurrentUser: Boolean(initialState?.currentUser),
      pathname: typeof window !== 'undefined' ? window.location.pathname : '',
    });

    if (loading) return;

    if (initialState?.currentUser) {
      bearerHydrateStarted.current = false;
      awaitingModelAfterSilentHydrate.current = false;
      return;
    }

    if (silentInFlight.current) return;

    if (awaitingModelAfterSilentHydrate.current) {
      authDebug('requireSession:awaitingModelAfterSilentHydrate', {});
      return;
    }

    const bearer = typeof window !== 'undefined' ? localStorage.getItem(STORAGE_BEARER_KEY) : null;

    if (bearer && !bearerHydrateStarted.current) {
      bearerHydrateStarted.current = true;
      silentInFlight.current = true;
      void (async () => {
        try {
          const u = await request<API.CurrentUser>('/api/v1/auth/session', {
            method: 'GET',
            skipErrorHandler: true,
            credentials: 'include',
          });
          if (u) {
            awaitingModelAfterSilentHydrate.current = true;
            try {
              await ensureTenantSelection(u);
              const gated = Boolean(u.needs_mfa);
              await setInitialState((s) => ({
                ...s,
                currentUser: u,
                canAdmin: Boolean(u && !gated && u.role === 'admin'),
                canWrite: Boolean(u && !gated && (u.role === 'admin' || u.role === 'operator')),
                canInviteMembers: Boolean(
                  u && !gated && u.tenants?.some((t) => t.membership_role === 'tenant_admin'),
                ),
              }));
              authDebug('requireSession:silentHydrateOk', { principal: u.principal_label });
            } catch {
              awaitingModelAfterSilentHydrate.current = false;
              bearerHydrateStarted.current = false;
              authDebug('requireSession:silentHydrateSetStateFailed', {});
              history.replace(redirectHref);
            }
          } else {
            authDebug('requireSession:silentHydrateEmpty', {});
            history.replace(redirectHref);
          }
        } catch (e) {
          const status = (e as { response?: { status?: number } })?.response?.status;
          authDebug('requireSession:silentHydrateError', { httpStatus: status ?? 'unknown' });
          history.replace(redirectHref);
        } finally {
          silentInFlight.current = false;
        }
      })();
      return;
    }

    authDebug('requireSession:replaceToLogin', {
      redirectHref,
      hadBearer: Boolean(bearer),
      bearerHydrateStarted: bearerHydrateStarted.current,
    });
    history.replace(redirectHref);
  }, [loading, initialState?.currentUser, redirectHref, setInitialState]);

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
