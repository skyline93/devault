import { EyeOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { useAccess, request } from '@umijs/max';
import { App, Button, Drawer, Space, Tag } from 'antd';
import React, { useRef, useState } from 'react';

const TERMINAL = new Set(['success', 'failed', 'cancelled']);

const JobsPage: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
  const actionRef = useRef<ActionType>();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [detail, setDetail] = useState<API.JobOut | null>(null);

  const openDetail = (row: API.JobOut) => {
    setDetail(row);
    setDrawerOpen(true);
  };

  const columns: ProColumns<API.JobOut>[] = [
    {
      title: '创建时间',
      dataIndex: 'created_at',
      valueType: 'dateTime',
      width: 170,
      sorter: (a, b) => a.created_at.localeCompare(b.created_at),
    },
    { title: '类型', dataIndex: 'kind', width: 120, valueType: 'select', valueEnum: {
      backup: { text: 'backup' },
      restore: { text: 'restore' },
      restore_drill: { text: 'restore_drill' },
      path_precheck: { text: 'path_precheck' },
    } },
    { title: '状态', dataIndex: 'status', width: 100, render: (_, r) => <Tag>{r.status}</Tag> },
    { title: '插件', dataIndex: 'plugin', width: 80 },
    { title: '触发', dataIndex: 'trigger', width: 100 },
    {
      title: '租约主机',
      dataIndex: 'lease_agent_hostname',
      ellipsis: true,
      copyable: true,
    },
    {
      title: '完成主机',
      dataIndex: 'completed_agent_hostname',
      ellipsis: true,
      copyable: true,
    },
    {
      title: '错误',
      dataIndex: 'error_message',
      ellipsis: true,
      hideInSearch: true,
    },
    {
      title: '操作',
      valueType: 'option',
      width: 220,
      render: (_, row) => (
        <Space size="small" wrap>
          <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => openDetail(row)}>
            详情
          </Button>
          {access.canWrite && !TERMINAL.has(row.status) ? (
            <Button
              type="link"
              size="small"
              danger
              onClick={async () => {
                await request(`/api/v1/jobs/${row.id}/cancel`, { method: 'POST' });
                message.success('已取消');
                actionRef.current?.reload();
              }}
            >
              取消
            </Button>
          ) : null}
          {access.canWrite && row.status === 'failed' && row.kind === 'backup' ? (
            <Button
              type="link"
              size="small"
              onClick={async () => {
                const res = await request<{ job_id: string; status: string }>(
                  `/api/v1/jobs/${row.id}/retry`,
                  { method: 'POST' },
                );
                message.success(`已重试，新作业 ${res.job_id}`);
                actionRef.current?.reload();
              }}
            >
              重试
            </Button>
          ) : null}
        </Space>
      ),
    },
  ];

  return (
    <PageContainer title="作业中心">
      <ProTable<API.JobOut>
        rowKey="id"
        actionRef={actionRef}
        columns={columns}
        search={{ labelWidth: 'auto' }}
        request={async (params) => {
          const qp: Record<string, string | number> = { limit: 200, offset: 0 };
          if (params.kind) qp.kind = String(params.kind);
          if (params.status) qp.status = String(params.status);
          const raw = await request<API.JobOut[]>('/api/v1/jobs', { params: qp });
          const data = [...raw].sort((a, b) => b.created_at.localeCompare(a.created_at));
          return { data, success: true, total: data.length };
        }}
        pagination={{ pageSize: 20 }}
        toolBarRender={() => []}
      />
      <Drawer
        title={detail ? `作业 ${detail.id}` : '详情'}
        width={720}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        destroyOnClose
      >
        {detail ? (
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <div>
              <strong>config_snapshot</strong>
              <pre
                style={{
                  marginTop: 8,
                  maxHeight: 280,
                  overflow: 'auto',
                  fontSize: 12,
                  background: '#f5f5f5',
                  padding: 12,
                  borderRadius: 8,
                }}
              >
                {JSON.stringify(detail.config_snapshot, null, 2)}
              </pre>
            </div>
            <div>
              <strong>result_meta</strong>
              <pre
                style={{
                  marginTop: 8,
                  maxHeight: 220,
                  overflow: 'auto',
                  fontSize: 12,
                  background: '#f5f5f5',
                  padding: 12,
                  borderRadius: 8,
                }}
              >
                {detail.result_meta == null
                  ? 'null'
                  : JSON.stringify(detail.result_meta, null, 2)}
              </pre>
            </div>
            <p>
              <strong>lease_agent_hostname</strong>：{detail.lease_agent_hostname ?? '—'}
            </p>
            <p>
              <strong>completed_agent_hostname</strong>：{detail.completed_agent_hostname ?? '—'}
            </p>
            <p>
              <strong>policy_id</strong>：{detail.policy_id ?? '—'}
            </p>
            <p>
              <strong>trace_id</strong>：{detail.trace_id ?? '—'}
            </p>
          </Space>
        ) : null}
      </Drawer>
    </PageContainer>
  );
};

export default JobsPage;
