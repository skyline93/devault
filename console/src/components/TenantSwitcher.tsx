import { request, useModel, useIntl } from '@umijs/max';
import { Select, Space, Tooltip, Typography, message } from 'antd';
import React, { useEffect, useMemo, useState } from 'react';

import { STORAGE_TENANT_ID_KEY } from '@/constants/storage';
import { authDebug } from '@/utils/auth-debug';

const TenantSwitcher: React.FC = () => {
  const { formatMessage } = useIntl();
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
      } catch (e) {
        const status = (e as { response?: { status?: number } })?.response?.status;
        authDebug('tenantSwitcher:tenantsRequestFailed', { httpStatus: status ?? 'unknown' });
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

  const selectedLabel = useMemo(() => {
    if (!value) return undefined;
    return options.find((o) => o.value === value)?.label;
  }, [options, value]);

  if (!user) return null;

  const tooltipTitle = selectedLabel
    ? formatMessage({ id: 'component.tenantTooltipSelected' }, { label: selectedLabel })
    : formatMessage({ id: 'component.tenantTooltipEmpty' });

  return (
    <Space size={6} align="center" className="ant-pro-global-header-index-action" style={{ marginInline: 8 }}>
      <Typography.Text type="secondary" style={{ fontSize: 12, whiteSpace: 'nowrap' }}>
        {formatMessage({ id: 'component.tenantCurrent' })}
      </Typography.Text>
      <Tooltip title={tooltipTitle}>
        <Select
          style={{ minWidth: 220 }}
          loading={loading}
          placeholder={formatMessage({ id: 'component.tenantSelectPlaceholder' })}
          value={options.some((o) => o.value === value) ? value : undefined}
          options={options}
          onChange={(id: string) => {
            localStorage.setItem(STORAGE_TENANT_ID_KEY, id);
            message.success(formatMessage({ id: 'component.tenantSwitched' }));
            window.location.reload();
          }}
          showSearch
          optionFilterProp="label"
        />
      </Tooltip>
    </Space>
  );
};

export default TenantSwitcher;
