import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { request, useIntl } from '@umijs/max';
import { Button, Tag } from 'antd';
import React, { useMemo, useState } from 'react';
import AgentSnapshotDrawer from '../AgentSnapshotDrawer';
import { agentPrimaryLabel } from '../agentDisplay';

const FleetPage: React.FC = () => {
  const { formatMessage } = useIntl();
  const [snapshotOpen, setSnapshotOpen] = useState(false);
  const [snapshotAgentId, setSnapshotAgentId] = useState<string | undefined>();

  const unknownHost = formatMessage({ id: 'page.policies.agentHostnameUnknown' });

  const columns: ProColumns<API.EdgeAgentOut>[] = useMemo(
    () => [
      {
        title: formatMessage({ id: 'page.fleet.colHostname' }),
        dataIndex: 'hostname',
        ellipsis: true,
        render: (_, r) => (
          <Button
            type="link"
            style={{ padding: 0, height: 'auto' }}
            onClick={() => {
              setSnapshotAgentId(r.id);
              setSnapshotOpen(true);
            }}
          >
            {agentPrimaryLabel(r.hostname, unknownHost)}
          </Button>
        ),
      },
      { title: formatMessage({ id: 'page.fleet.colVersion' }), dataIndex: 'agent_release', width: 120 },
      {
        title: formatMessage({ id: 'page.fleet.colTenants' }),
        dataIndex: 'allowed_tenant_ids',
        ellipsis: true,
        render: (_, r) =>
          r.allowed_tenant_ids?.length
            ? formatMessage({ id: 'page.fleet.tenantCount' }, { count: r.allowed_tenant_ids.length })
            : '—',
      },
      {
        title: formatMessage({ id: 'page.fleet.colCompat' }),
        key: 'gates',
        width: 200,
        render: (_, r) => (
          <span>
            {r.meets_min_supported_version ? (
              <Tag color="green">{formatMessage({ id: 'page.fleet.tagVersionOk' })}</Tag>
            ) : (
              <Tag>{formatMessage({ id: 'page.fleet.tagVersionWarn' })}</Tag>
            )}
            {r.proto_matches_control_plane ? (
              <Tag color="blue">{formatMessage({ id: 'page.fleet.tagProtoOk' })}</Tag>
            ) : (
              <Tag color="orange">{formatMessage({ id: 'page.fleet.tagProtoWarn' })}</Tag>
            )}
          </span>
        ),
      },
      { title: formatMessage({ id: 'page.fleet.colHeartbeat' }), dataIndex: 'last_seen_at', valueType: 'dateTime', width: 170 },
    ],
    [formatMessage, unknownHost],
  );

  return (
    <PageContainer title={formatMessage({ id: 'page.fleet.title' })}>
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
      <AgentSnapshotDrawer
        open={snapshotOpen}
        agentId={snapshotAgentId}
        onClose={() => {
          setSnapshotOpen(false);
          setSnapshotAgentId(undefined);
        }}
      />
    </PageContainer>
  );
};

export default FleetPage;
