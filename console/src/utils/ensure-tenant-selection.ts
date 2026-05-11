import { request as maxRequest } from '@umijs/max';

import { STORAGE_TENANT_ID_KEY } from '@/constants/storage';

/** 与 `getInitialState` 一致：按当前用户可见租户校正 `X-DeVault-Tenant-Id` 本地缓存。 */
export async function ensureTenantSelection(user: API.CurrentUser): Promise<void> {
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
