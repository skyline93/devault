import { PageContainer, ProCard, ProTable } from '@ant-design/pro-components';
import { Link, request, useIntl, useModel } from '@umijs/max';
import { Button, Space, Tag, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import React, { useEffect, useMemo, useState } from 'react';

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
  const { formatMessage } = useIntl();
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

  const columns: ColumnsType<API.JobRow> = useMemo(
    () => [
      { title: formatMessage({ id: 'page.workbench.colCreated' }), dataIndex: 'created_at', width: 200, ellipsis: true },
      { title: formatMessage({ id: 'page.workbench.colKind' }), dataIndex: 'kind', width: 120 },
      {
        title: formatMessage({ id: 'page.workbench.colStatus' }),
        dataIndex: 'status',
        width: 110,
        render: (s: string) => <Tag color={statusColor(s)}>{s}</Tag>,
      },
      { title: formatMessage({ id: 'page.workbench.colPlugin' }), dataIndex: 'plugin', width: 90 },
      { title: formatMessage({ id: 'page.workbench.colErrorCode' }), dataIndex: 'error_code', ellipsis: true },
      { title: formatMessage({ id: 'page.workbench.colErrorMessage' }), dataIndex: 'error_message', ellipsis: true },
    ],
    [formatMessage],
  );

  return (
    <PageContainer title={formatMessage({ id: 'page.workbench.title' })}>
      <ProCard title={formatMessage({ id: 'page.workbench.versionCard' })} style={{ marginBottom: 16 }} bordered>
        {version ? (
          <Typography.Paragraph copyable style={{ marginBottom: 0 }}>
            <strong>{version.service}</strong> · <code>{version.version}</code> · API {version.api}
            {version.grpc_proto_package ? ` · proto ${version.grpc_proto_package}` : null}
            {version.git_sha ? ` · git ${version.git_sha}` : null}
          </Typography.Paragraph>
        ) : (
          <Typography.Text type="secondary">{formatMessage({ id: 'page.workbench.versionUnavailable' })}</Typography.Text>
        )}
      </ProCard>

      <ProCard title={formatMessage({ id: 'page.workbench.observabilityCard' })} style={{ marginBottom: 16 }} bordered>
        <Typography.Paragraph type="secondary" style={{ marginTop: 0 }}>
          {formatMessage({ id: 'page.workbench.observabilityIntro' })}
        </Typography.Paragraph>
        <Space wrap>
          <Button type="link" href="/metrics" target="_blank" rel="noreferrer">
            {formatMessage({ id: 'page.workbench.metricsLink' })}
          </Button>
          {grafanaUrl ? (
            <Button type="primary" href={grafanaUrl} target="_blank" rel="noreferrer">
              {formatMessage({ id: 'page.workbench.openGrafana' })}
            </Button>
          ) : (
            <Typography.Text type="secondary">{formatMessage({ id: 'page.workbench.grafanaEnvHint' })}</Typography.Text>
          )}
        </Space>
      </ProCard>

      <ProCard title={formatMessage({ id: 'page.workbench.jobsCard' })} bordered loading={loading}>
        <Typography.Paragraph type="secondary" style={{ marginTop: 0 }}>
          {formatMessage({ id: 'page.workbench.jobsIntro' })}{' '}
          <Link to="/backup/jobs">{formatMessage({ id: 'menu.backup.jobs' })}</Link>.
        </Typography.Paragraph>
        <ProTable<API.JobRow>
          search={false}
          options={false}
          pagination={false}
          rowKey="id"
          columns={columns}
          dataSource={jobs}
          locale={{ emptyText: formatMessage({ id: 'page.workbench.jobsEmpty' }) }}
        />
      </ProCard>
    </PageContainer>
  );
};

export default Workbench;
