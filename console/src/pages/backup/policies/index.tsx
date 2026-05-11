import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { history, Link, request, useAccess, useIntl } from '@umijs/max';
import { App, Button, Modal, Space, Tag } from 'antd';
import React, { useMemo, useRef } from 'react';

const PoliciesPage: React.FC = () => {
  const { formatMessage } = useIntl();
  const { message } = App.useApp();
  const access = useAccess();
  const actionRef = useRef<ActionType>();

  const columns: ProColumns<API.PolicyOut>[] = useMemo(
    () => [
      { title: formatMessage({ id: 'page.policies.colName' }), dataIndex: 'name', ellipsis: true },
      { title: formatMessage({ id: 'page.policies.colPlugin' }), dataIndex: 'plugin', width: 80 },
      {
        title: formatMessage({ id: 'page.policies.colEnabled' }),
        dataIndex: 'enabled',
        width: 80,
        render: (_, r) =>
          r.enabled ? (
            <Tag color="green">{formatMessage({ id: 'page.policies.yes' })}</Tag>
          ) : (
            <Tag>{formatMessage({ id: 'page.policies.no' })}</Tag>
          ),
      },
      {
        title: formatMessage({ id: 'page.policies.colAgent' }),
        dataIndex: 'bound_agent_id',
        ellipsis: true,
        render: (_, r) =>
          r.bound_agent_id ? (
            <Link to={`/execution/fleet/${r.bound_agent_id}`}>{r.bound_agent_id}</Link>
          ) : (
            '—'
          ),
      },
      {
        title: formatMessage({ id: 'page.policies.colPool' }),
        dataIndex: 'bound_agent_pool_id',
        ellipsis: true,
        render: (_, r) =>
          r.bound_agent_pool_id ? (
            <Link to={`/execution/agent-pools/${r.bound_agent_pool_id}`}>{r.bound_agent_pool_id}</Link>
          ) : (
            '—'
          ),
      },
      { title: formatMessage({ id: 'page.policies.colCreated' }), dataIndex: 'created_at', valueType: 'dateTime', width: 170 },
      {
        title: formatMessage({ id: 'page.policies.colActions' }),
        valueType: 'option',
        width: 160,
        render: (_, row) => (
          <Space>
            <Button type="link" size="small" onClick={() => history.push(`/backup/policies/${row.id}`)}>
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
    [access.canWrite, formatMessage, message],
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
          const data = await request<API.PolicyOut[]>('/api/v1/policies');
          return { data, success: true, total: data.length };
        }}
        pagination={{ pageSize: 20 }}
      />
    </PageContainer>
  );
};

export default PoliciesPage;
