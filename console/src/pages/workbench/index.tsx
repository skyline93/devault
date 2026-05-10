import { PageContainer, ProCard, ProTable } from '@ant-design/pro-components';
import { Link, request, useModel } from '@umijs/max';
import { Button, Space, Tag, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import React, { useEffect, useState } from 'react';

const ACTIVE_STATUSES = new Set(['pending', 'running', 'uploading', 'verifying', 'retrying']);

const statusColor = (s: string) => {
  if (s === 'failed') return 'error';
  if (s === 'success') return 'success';
  if (ACTIVE_STATUSES.has(s)) return 'processing';
  if (s === 'cancelled') return 'default';
  return 'default';
};

const grafanaUrl = (process.env.UMI_APP_GRAFANA_URL || '').trim();

const Workbench: React.FC = () => {
  const { initialState } = useModel('@@initialState');
  const [version, setVersion] = useState<API.VersionInfo | null>(null);
  const [jobs, setJobs] = useState<API.JobRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [v, j] = await Promise.all([
          request<API.VersionInfo>('/version', { method: 'GET', skipErrorHandler: true }),
          request<API.JobRow[]>('/api/v1/jobs', { method: 'GET', params: { limit: 50, offset: 0 } }),
        ]);
        if (!cancelled) {
          setVersion(v);
          const interesting = j.filter(
            (row) => row.status === 'failed' || ACTIVE_STATUSES.has(row.status),
          );
          setJobs(interesting.slice(0, 15));
        }
      } catch {
        if (!cancelled) {
          setVersion(null);
          setJobs([]);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [initialState?.currentUser]);

  const columns: ColumnsType<API.JobRow> = [
    { title: '创建时间', dataIndex: 'created_at', width: 200, ellipsis: true },
    { title: '类型', dataIndex: 'kind', width: 120 },
    { title: '状态', dataIndex: 'status', width: 110, render: (s: string) => <Tag color={statusColor(s)}>{s}</Tag> },
    { title: '插件', dataIndex: 'plugin', width: 90 },
    { title: '错误码', dataIndex: 'error_code', ellipsis: true },
    { title: '错误信息', dataIndex: 'error_message', ellipsis: true },
  ];

  return (
    <PageContainer title="工作台">
      <ProCard title="控制面版本（GET /version）" style={{ marginBottom: 16 }} bordered>
        {version ? (
          <Typography.Paragraph copyable style={{ marginBottom: 0 }}>
            <strong>{version.service}</strong> · <code>{version.version}</code> · API {version.api}
            {version.grpc_proto_package ? ` · proto ${version.grpc_proto_package}` : null}
            {version.git_sha ? ` · git ${version.git_sha}` : null}
          </Typography.Paragraph>
        ) : (
          <Typography.Text type="secondary">无法加载 /version（检查代理与控制面是否运行）</Typography.Text>
        )}
      </ProCard>

      <ProCard title="指标与看板（十五-24）" style={{ marginBottom: 16 }} bordered>
        <Typography.Paragraph type="secondary" style={{ marginTop: 0 }}>
          与顶栏<strong>帮助</strong>一致：同源 <Typography.Text code>/metrics</Typography.Text>、
          <Typography.Text code>/version</Typography.Text> 等由 nginx/代理转发到控制面。部署 Prometheus + Grafana
          时参见文档站 <Typography.Text code>install/observability</Typography.Text>。
        </Typography.Paragraph>
        <Space wrap>
          <Button type="link" href="/metrics" target="_blank" rel="noreferrer">
            Prometheus 指标（/metrics）
          </Button>
          {grafanaUrl ? (
            <Button type="primary" href={grafanaUrl} target="_blank" rel="noreferrer">
              打开 Grafana
            </Button>
          ) : (
            <Typography.Text type="secondary">
              构建前设置环境变量 <Typography.Text code>UMI_APP_GRAFANA_URL</Typography.Text> 可在此显示 Grafana
              按钮（见 <Typography.Text code>console/.env.example</Typography.Text>）。
            </Typography.Text>
          )}
        </Space>
      </ProCard>

      <ProCard title="最近失败或进行中的作业（当前租户）" bordered loading={loading}>
        <Typography.Paragraph type="secondary" style={{ marginTop: 0 }}>
          数据来源 <Typography.Text code>GET /api/v1/jobs?limit=50</Typography.Text>
          ，前端筛选 <Typography.Text code>failed</Typography.Text> 与进行中状态；可按需在 API 使用{' '}
          <Typography.Text code>kind</Typography.Text> / <Typography.Text code>status</Typography.Text> 查询参数（十五-23）。完整列表见{' '}
          <Link to="/backup/jobs">作业中心</Link>。
        </Typography.Paragraph>
        <ProTable<API.JobRow>
          search={false}
          options={false}
          pagination={false}
          rowKey="id"
          columns={columns}
          dataSource={jobs}
          locale={{ emptyText: '暂无失败或进行中的作业' }}
        />
      </ProCard>
    </PageContainer>
  );
};

export default Workbench;
