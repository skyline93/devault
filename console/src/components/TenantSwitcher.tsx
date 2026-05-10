import { request, useModel } from '@umijs/max';
import { Select, message } from 'antd';
import React, { useEffect, useMemo, useState } from 'react';

import { STORAGE_TENANT_ID_KEY } from '@/constants/storage';

/**
 * 顶栏租户选择（十五-07）：`GET /api/v1/tenants`（服务端已按 token 过滤）+ 本地持久化 UUID。
 * 替代旧 Jinja **`devault_ui_tenant` Cookie** / **`POST /ui/context/tenant`**。
 */
const TenantSwitcher: React.FC = () => {
  const { initialState } = useModel('@@initialState');
  const user = initialState?.currentUser;
  const [tenants, setTenants] = useState<API.TenantRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) {
      setTenants([]);
      setLoading(false);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const rows = await request<API.TenantRow[]>('/api/v1/tenants');
        if (!cancelled) setTenants(rows);
      } catch {
        if (!cancelled) setTenants([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [user]);

  const options = useMemo(() => {
    if (!user) return [];
    const allow = user.allowed_tenant_ids;
    const list = allow === null ? tenants : tenants.filter((t) => allow.includes(t.id));
    return list.map((t) => ({ value: t.id, label: `${t.name}（${t.slug}）` }));
  }, [tenants, user]);

  const value = typeof window !== 'undefined' ? localStorage.getItem(STORAGE_TENANT_ID_KEY) ?? undefined : undefined;

  if (!user) return null;

  return (
    <Select
      className="ant-pro-global-header-index-action"
      style={{ minWidth: 220, marginInline: 8 }}
      loading={loading}
      placeholder="租户"
      value={options.some((o) => o.value === value) ? value : undefined}
      options={options}
      onChange={(id: string) => {
        localStorage.setItem(STORAGE_TENANT_ID_KEY, id);
        message.success('已切换租户');
        window.location.reload();
      }}
      showSearch
      optionFilterProp="label"
    />
  );
};

export default TenantSwitcher;
