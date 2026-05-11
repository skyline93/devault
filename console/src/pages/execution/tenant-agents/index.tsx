import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Link, request, useIntl } from '@umijs/max';
import { Tag } from 'antd';
import React, { useMemo } from 'react';

const TenantAgentsPage: React.FC = () => {
  const { formatMessage } = useIntl();
  const columns: ProColumns<API.TenantScopedAgentOut>[] = useMemo(
    () => [
      {
        title: formatMessage({ id: 'page.tenantAgents.colAgentId' }),
        dataIndex: 'id',
        copyable: true,
        render: (_, r) => <Link to={`/execution/fleet/${r.id}`}>{r.id}</Link>,
      },
      { title: formatMessage({ id: 'page.tenantAgents.colHostname' }), dataIndex: 'hostname', ellipsis: true },
      { title: formatMessage({ id: 'page.tenantAgents.colVersion' }), dataIndex: 'agent_release', width: 120 },
      {
        title: formatMessage({ id: 'page.tenantAgents.colGate' }),
        dataIndex: 'meets_min_supported_version',
        width: 100,
        render: (_, r) =>
          r.meets_min_supported_version ? (
            <Tag color="green">{formatMessage({ id: 'page.tenantAgents.gateOk' })}</Tag>
          ) : (
            <Tag color="red">{formatMessage({ id: 'page.tenantAgents.gateLow' })}</Tag>
          ),
      },
      { title: formatMessage({ id: 'page.tenantAgents.colHeartbeat' }), dataIndex: 'last_seen_at', valueType: 'dateTime', width: 170 },
      {
        title: formatMessage({ id: 'page.tenantAgents.colAllowlist' }),
        dataIndex: 'backup_path_allowlist',
        ellipsis: true,
        hideInSearch: true,
        render: (_, r) => (r.backup_path_allowlist?.length ? r.backup_path_allowlist.join(', ') : '—'),
      },
    ],
    [formatMessage],
  );

  return (
    <PageContainer title={formatMessage({ id: 'page.tenantAgents.title' })}>
      <ProTable<API.TenantScopedAgentOut>
        rowKey="id"
        columns={columns}
        search={false}
        request={async () => {
          const data = await request<API.TenantScopedAgentOut[]>('/api/v1/tenant-agents');
          return { data, success: true, total: data.length };
        }}
        pagination={{ pageSize: 20 }}
      />
    </PageContainer>
  );
};

export default TenantAgentsPage;
