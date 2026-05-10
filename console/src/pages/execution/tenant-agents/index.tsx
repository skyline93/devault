import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Link, request } from '@umijs/max';
import { Tag } from 'antd';
import React from 'react';

const TenantAgentsPage: React.FC = () => {
  const columns: ProColumns<API.TenantScopedAgentOut>[] = [
    {
      title: 'Agent ID',
      dataIndex: 'id',
      copyable: true,
      render: (_, r) => <Link to={`/execution/fleet/${r.id}`}>{r.id}</Link>,
    },
    { title: '主机名', dataIndex: 'hostname', ellipsis: true },
    { title: '版本', dataIndex: 'agent_release', width: 120 },
    {
      title: '版本门槛',
      dataIndex: 'meets_min_supported_version',
      width: 100,
      render: (_, r) => (r.meets_min_supported_version ? <Tag color="green">OK</Tag> : <Tag color="red">低</Tag>),
    },
    { title: '最近心跳', dataIndex: 'last_seen_at', valueType: 'dateTime', width: 170 },
    {
      title: 'allowlist',
      dataIndex: 'backup_path_allowlist',
      ellipsis: true,
      hideInSearch: true,
      render: (_, r) => (r.backup_path_allowlist?.length ? r.backup_path_allowlist.join(', ') : '—'),
    },
  ];

  return (
    <PageContainer title="租户内 Agents">
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
