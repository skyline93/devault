import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { history, Link, request, useAccess } from '@umijs/max';
import { App, Button, Modal, Space, Tag } from 'antd';
import React, { useRef } from 'react';

const PoliciesPage: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
  const actionRef = useRef<ActionType>();

  const columns: ProColumns<API.PolicyOut>[] = [
    { title: '名称', dataIndex: 'name', ellipsis: true },
    { title: '插件', dataIndex: 'plugin', width: 80 },
    {
      title: '启用',
      dataIndex: 'enabled',
      width: 80,
      render: (_, r) => (r.enabled ? <Tag color="green">是</Tag> : <Tag>否</Tag>),
    },
    {
      title: '绑定 Agent',
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
      title: '绑定池',
      dataIndex: 'bound_agent_pool_id',
      ellipsis: true,
      render: (_, r) =>
        r.bound_agent_pool_id ? (
          <Link to={`/execution/agent-pools/${r.bound_agent_pool_id}`}>{r.bound_agent_pool_id}</Link>
        ) : (
          '—'
        ),
    },
    { title: '创建时间', dataIndex: 'created_at', valueType: 'dateTime', width: 170 },
    {
      title: '操作',
      valueType: 'option',
      width: 160,
      render: (_, row) => (
        <Space>
          <Button type="link" size="small" onClick={() => history.push(`/backup/policies/${row.id}`)}>
            编辑
          </Button>
          {access.canWrite ? (
            <Button
              type="link"
              size="small"
              danger
              onClick={() => {
                Modal.confirm({
                  title: '删除策略？',
                  content: '将删除该策略及其关联计划需另行处理；请确认无依赖。',
                  onOk: async () => {
                    await request(`/api/v1/policies/${row.id}`, { method: 'DELETE' });
                    message.success('已删除');
                    actionRef.current?.reload();
                  },
                });
              }}
            >
              删除
            </Button>
          ) : null}
        </Space>
      ),
    },
  ];

  return (
    <PageContainer
      title="策略"
      extra={
        access.canWrite ? (
          <Button type="primary" icon={<PlusOutlined />} onClick={() => history.push('/backup/policies/new')}>
            新建策略
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
