import { EyeOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { request, useAccess, useIntl } from '@umijs/max';
import { App, Button, Drawer, Space, Tag } from 'antd';
import React, { useMemo, useRef, useState } from 'react';

const TERMINAL = new Set(['success', 'failed', 'cancelled']);

const JobsPage: React.FC = () => {
  const { formatMessage } = useIntl();
  const { message } = App.useApp();
  const access = useAccess();
  const actionRef = useRef<ActionType>();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [detail, setDetail] = useState<API.JobOut | null>(null);

  const openDetail = (row: API.JobOut) => {
    setDetail(row);
    setDrawerOpen(true);
  };

  const columns: ProColumns<API.JobOut>[] = useMemo(
    () => [
      {
        title: formatMessage({ id: 'page.jobs.colCreated' }),
        dataIndex: 'created_at',
        valueType: 'dateTime',
        width: 170,
        sorter: (a, b) => a.created_at.localeCompare(b.created_at),
      },
      {
        title: formatMessage({ id: 'page.jobs.colKind' }),
        dataIndex: 'kind',
        width: 120,
        valueType: 'select',
        valueEnum: {
          backup: { text: 'backup' },
          restore: { text: 'restore' },
          restore_drill: { text: 'restore_drill' },
          path_precheck: { text: 'path_precheck' },
        },
      },
      {
        title: formatMessage({ id: 'page.jobs.colStatus' }),
        dataIndex: 'status',
        width: 100,
        render: (_, r) => <Tag>{r.status}</Tag>,
      },
      { title: formatMessage({ id: 'page.jobs.colPlugin' }), dataIndex: 'plugin', width: 80 },
      { title: formatMessage({ id: 'page.jobs.colTrigger' }), dataIndex: 'trigger', width: 100 },
      {
        title: formatMessage({ id: 'page.jobs.colLeaseHost' }),
        dataIndex: 'lease_agent_hostname',
        ellipsis: true,
        copyable: true,
      },
      {
        title: formatMessage({ id: 'page.jobs.colFinishHost' }),
        dataIndex: 'completed_agent_hostname',
        ellipsis: true,
        copyable: true,
      },
      {
        title: formatMessage({ id: 'page.jobs.colError' }),
        dataIndex: 'error_message',
        ellipsis: true,
        hideInSearch: true,
      },
      {
        title: formatMessage({ id: 'page.jobs.colActions' }),
        valueType: 'option',
        width: 220,
        render: (_, row) => (
          <Space size="small" wrap>
            <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => openDetail(row)}>
              {formatMessage({ id: 'page.jobs.detail' })}
            </Button>
            {access.canWrite && !TERMINAL.has(row.status) ? (
              <Button
                type="link"
                size="small"
                danger
                onClick={async () => {
                  await request(`/api/v1/jobs/${row.id}/cancel`, { method: 'POST' });
                  message.success(formatMessage({ id: 'page.jobs.cancelled' }));
                  actionRef.current?.reload();
                }}
              >
                {formatMessage({ id: 'page.jobs.cancel' })}
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
                  message.success(formatMessage({ id: 'page.jobs.retried' }, { jobId: res.job_id }));
                  actionRef.current?.reload();
                }}
              >
                {formatMessage({ id: 'page.jobs.retry' })}
              </Button>
            ) : null}
          </Space>
        ),
      },
    ],
    [access.canWrite, formatMessage, message],
  );

  const dash = '—';

  return (
    <PageContainer title={formatMessage({ id: 'page.jobs.title' })}>
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
        title={
          detail
            ? formatMessage({ id: 'page.jobs.drawerTitle' }, { jobId: detail.id })
            : formatMessage({ id: 'page.jobs.detail' })
        }
        width={720}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        destroyOnClose
      >
        {detail ? (
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <div>
              <strong>{formatMessage({ id: 'page.jobs.snapshotConfig' })}</strong>
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
              <strong>{formatMessage({ id: 'page.jobs.resultMeta' })}</strong>
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
                {detail.result_meta == null ? 'null' : JSON.stringify(detail.result_meta, null, 2)}
              </pre>
            </div>
            <p>
              <strong>{formatMessage({ id: 'page.jobs.leaseHost' })}</strong>：{detail.lease_agent_hostname ?? dash}
            </p>
            <p>
              <strong>{formatMessage({ id: 'page.jobs.completeHost' })}</strong>：{detail.completed_agent_hostname ?? dash}
            </p>
            <p>
              <strong>{formatMessage({ id: 'page.jobs.policyRef' })}</strong>：{detail.policy_id ?? dash}
            </p>
            <p>
              <strong>{formatMessage({ id: 'page.jobs.traceRef' })}</strong>：{detail.trace_id ?? dash}
            </p>
          </Space>
        ) : null}
      </Drawer>
    </PageContainer>
  );
};

export default JobsPage;
