import type { RequestConfig } from '@umijs/max';
import { message } from 'antd';

import { LOGIN_PATH } from '@/constants/auth-routes';
import { CSRF_COOKIE_NAME, STORAGE_BEARER_KEY, STORAGE_TENANT_ID_KEY } from '@/constants/storage';
import { authDebug } from '@/utils/auth-debug';

function readCookie(name: string): string | null {
  if (typeof document === 'undefined') return null;
  const esc = name.replace(/([.$?*|{}()[\]\\/+^])/g, '\\$1');
  const m = document.cookie.match(new RegExp(`(?:^|; )${esc}=([^;]*)`));
  return m ? decodeURIComponent(m[1]) : null;
}

export function detailFromError(error: unknown): string {
  const body = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof body === 'string') return body;
  if (Array.isArray(body)) {
    return body
      .map((x) =>
        typeof x === 'object' && x && 'msg' in x ? String((x as { msg: string }).msg) : String(x),
      )
      .join('; ');
  }
  return (error as Error)?.message || '请求失败';
}

export const errorConfig: RequestConfig = {
  errorConfig: {
    errorHandler: (error: unknown, opts: { skipErrorHandler?: boolean } | undefined) => {
      if (opts?.skipErrorHandler) throw error;
      const status = (error as { response?: { status?: number } })?.response?.status;
      if (status === 401) {
        if (typeof window !== 'undefined') {
          const { pathname, search, hash } = window.location;
          const reqUrl = (error as { request?: { url?: string }; config?: { url?: string } })?.request?.url
            ?? (error as { config?: { url?: string } })?.config?.url;
          authDebug('http:401', {
            pathname,
            requestUrl: reqUrl ?? 'unknown',
            willFullPageRedirect: pathname !== LOGIN_PATH,
          });
          localStorage.removeItem(STORAGE_BEARER_KEY);
          if (pathname !== LOGIN_PATH) {
            const redirect = encodeURIComponent(pathname + search + hash);
            window.location.href = `${LOGIN_PATH}?redirect=${redirect}`;
          }
        }
        return;
      }
      if (status === 403) {
        message.error(detailFromError(error) || '权限不足');
        return;
      }
      message.error(detailFromError(error));
    },
  },
  requestInterceptors: [
    (url: string, options: Record<string, unknown>) => {
      const headers: Record<string, string> = {
        ...((options.headers as Record<string, string> | undefined) ?? {}),
      };
      const token = typeof window !== 'undefined' ? localStorage.getItem(STORAGE_BEARER_KEY) : null;
      const tenant =
        typeof window !== 'undefined' ? localStorage.getItem(STORAGE_TENANT_ID_KEY) : null;
      if (token) headers.Authorization = `Bearer ${token}`;
      if (tenant) headers['X-DeVault-Tenant-Id'] = tenant;
      const method = String(options.method || 'GET').toUpperCase();
      if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
        const csrf = readCookie(CSRF_COOKIE_NAME);
        if (csrf) headers['X-CSRF-Token'] = csrf;
      }
      return {
        url,
        options: {
          ...options,
          headers,
          credentials: 'include' as RequestCredentials,
        },
      };
    },
  ],
};
