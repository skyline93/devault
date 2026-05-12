import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import AgentSnapshotDrawer from '../../execution/AgentSnapshotDrawer';
import { agentPrimaryLabel } from '../../execution/agentDisplay';
import { history, request, useAccess, useIntl, useLocation } from '@umijs/max';
import { App, Button, Modal, Space, Switch, Tag, Tooltip } from 'antd';
import React, { useMemo, useRef, useState } from 'react';
import PolicyEditDrawer from './PolicyEditDrawer';

const PoliciesPage: React.FC = () => {
  const { formatMessage } = useIntl();
  const { message } = App.useApp();
  const access = useAccess();
  const actionRef = useRef<ActionType>();
  const location = useLocation();
  const [enablingId, setEnablingId] = useState<string | undefined>();
  const [agentHosts, setAgentHosts] = useState<Record<string, string>>({});
  const [snapshotOpen, setSnapshotOpen] = useState(false);
  const [snapshotAgentId, setSnapshotAgentId] = useState<string | undefined>();

  const editId = useMemo(() => {
    const q = new URLSearchParams(location.search).get('edit');
    return q && q.length > 0 ? q : undefined;
  }, [location.search]);

  const closeDrawer = () => {
    history.replace('/backup/policies');
  };

  const unknownHost = formatMessage({ id: 'page.policies.agentHostnameUnknown' });

  const columns: ProColumns<API.PolicyOut>[] = useMemo(
    () => [
      {
        title: formatMessage({ id: 'page.policies.colCreated' }),
        dataIndex: 'created_at',
        valueType: 'dateTime',
        width: 170,
      },
      { title: formatMessage({ id: 'page.policies.colName' }), dataIndex: 'name', ellipsis: true },
      { title: formatMessage({ id: 'page.policies.colPlugin' }), dataIndex: 'plugin', width: 140 },
      {
        title: formatMessage({ id: 'page.policies.colAgentHost' }),
        dataIndex: 'bound_agent_id',
        ellipsis: true,
        render: (_, r) => {
          if (!r.bound_agent_id) return '—';
          const label = agentHosts[r.bound_agent_id] ?? unknownHost;
          return (
            <Tooltip title={r.bound_agent_id}>
              <Button
                type="link"
                style={{ padding: 0, height: 'auto' }}
                onClick={() => {
                  setSnapshotAgentId(r.bound_agent_id!);
                  setSnapshotOpen(true);
                }}
              >
                {label}
              </Button>
            </Tooltip>
          );
        },
      },
      {
        title: formatMessage({ id: 'page.policies.colActions' }),
        valueType: 'option',
        width: 280,
        render: (_, row) => (
          <Space size="small" wrap align="center">
            {access.canWrite ? (
              <Switch
                checked={row.enabled}
                loading={enablingId === row.id}
                onChange={(checked) => {
                  if (checked === row.enabled) return;
                  Modal.confirm({
                    title: checked
                      ? formatMessage({ id: 'page.policies.enableConfirmTitle' })
                      : formatMessage({ id: 'page.policies.disableConfirmTitle' }),
                    content: checked
                      ? formatMessage({ id: 'page.policies.enableConfirmContent' })
                      : formatMessage({ id: 'page.policies.disableConfirmContent' }),
                    onOk: async () => {
                      setEnablingId(row.id);
                      try {
                        await request(`/api/v1/policies/${row.id}`, {
                          method: 'PATCH',
                          data: { enabled: checked },
                        });
                        message.success(formatMessage({ id: 'page.policies.enabledUpdated' }));
                        actionRef.current?.reload();
                      } catch {
                        message.error(formatMessage({ id: 'page.policies.enableUpdateFailed' }));
                      } finally {
                        setEnablingId(undefined);
                      }
                    },
                  });
                }}
              />
            ) : row.enabled ? (
              <Tag color="green">{formatMessage({ id: 'page.policies.yes' })}</Tag>
            ) : (
              <Tag>{formatMessage({ id: 'page.policies.no' })}</Tag>
            )}
            <Button type="link" size="small" onClick={() => history.push(`/backup/policies?edit=${row.id}`)}>
              {formatMessage({ id: 'page.policies.edit' })}
            </Button>
            {access.canWrite ? (
              <Button
                type="link"
                size="small"
                danger
                onClick={() => {
                  Modal.confirm({
                    title: formatMessage({ id: 'page.policies.deleteTitle' }),
                    content: formatMessage({ id: 'page.policies.deleteContent' }),
                    onOk: async () => {
                      await request(`/api/v1/policies/${row.id}`, { method: 'DELETE' });
                      message.success(formatMessage({ id: 'page.policies.deleted' }));
                      actionRef.current?.reload();
                    },
                  });
                }}
              >
                {formatMessage({ id: 'page.policies.delete' })}
              </Button>
            ) : null}
          </Space>
        ),
      },
    ],
    [access.canWrite, agentHosts, enablingId, formatMessage, message, unknownHost],
  );

  return (
    <PageContainer
      title={formatMessage({ id: 'page.policies.title' })}
      extra={
        access.canWrite ? (
          <Button type="primary" icon={<PlusOutlined />} onClick={() => history.push('/backup/policies/new')}>
            {formatMessage({ id: 'page.policies.new' })}
          </Button>
        ) : undefined
      }
    >
      <ProTable<API.PolicyOut>
        rowKey="id"
        actionRef={actionRef}
        columns={columns}
        search={false}
        request={async () => {
          const [policies, agents] = await Promise.all([
            request<API.PolicyOut[]>('/api/v1/policies'),
            request<API.TenantScopedAgentOut[]>('/api/v1/tenant-agents'),
          ]);
          const m: Record<string, string> = {};
          for (const a of agents) {
            m[a.id] = agentPrimaryLabel(a.hostname, unknownHost);
          }
          setAgentHosts(m);
          return { data: policies, success: true, total: policies.length };
        }}
        pagination={{ pageSize: 20 }}
      />
      <PolicyEditDrawer
        open={Boolean(editId)}
        policyId={editId}
        onClose={closeDrawer}
        onSaved={() => actionRef.current?.reload()}
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

export default PoliciesPage;
