import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Link, request } from '@umijs/max';
import { Tag } from 'antd';
import React from 'react';

const FleetPage: React.FC = () => {
  const columns: ProColumns<API.EdgeAgentOut>[] = [
    {
      title: 'Agent ID',
      dataIndex: 'id',
      copyable: true,
      render: (_, r) => <Link to={`/execution/fleet/${r.id}`}>{r.id}</Link>,
    },
    { title: '主机名', dataIndex: 'hostname', ellipsis: true },
    { title: '版本', dataIndex: 'agent_release', width: 120 },
    {
      title: '登记租户',
      dataIndex: 'allowed_tenant_ids',
      ellipsis: true,
      render: (_, r) =>
        r.allowed_tenant_ids?.length ? `${r.allowed_tenant_ids.length} 个` : '—',
    },
    {
      title: '门槛/Proto',
      key: 'gates',
      width: 140,
      render: (_, r) => (
        <span>
          {r.meets_min_supported_version ? <Tag color="green">版本</Tag> : <Tag>版本</Tag>}
          {r.proto_matches_control_plane ? <Tag color="blue">Proto</Tag> : <Tag color="orange">Proto</Tag>}
        </span>
      ),
    },
    { title: '最近心跳', dataIndex: 'last_seen_at', valueType: 'dateTime', width: 170 },
  ];

  return (
    <PageContainer title="全舰队 Agents">
      <ProTable<API.EdgeAgentOut>
        rowKey="id"
        columns={columns}
        search={false}
        request={async () => {
          const data = await request<API.EdgeAgentOut[]>('/api/v1/agents', { params: { limit: 500, offset: 0 } });
          return { data, success: true, total: data.length };
        }}
        pagination={{ pageSize: 25 }}
      />
    </PageContainer>
  );
};

export default FleetPage;
