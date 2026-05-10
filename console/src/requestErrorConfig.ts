import type { RequestConfig } from '@umijs/max';
import { message } from 'antd';

import { STORAGE_BEARER_KEY, STORAGE_TENANT_ID_KEY } from '@/constants/storage';

const loginPath = '/user/login';

function detailFromError(error: unknown): string {
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
          localStorage.removeItem(STORAGE_BEARER_KEY);
          if (pathname !== loginPath) {
            const redirect = encodeURIComponent(pathname + search + hash);
            window.location.href = `${loginPath}?redirect=${redirect}`;
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
      return { url, options: { ...options, headers } };
    },
  ],
};
