import { EyeOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { request, useAccess, useIntl } from '@umijs/max';
import { App, Button, Drawer, Form, Input, Modal, Space, Switch, Tag, Typography } from 'antd';
import React, { useMemo, useRef, useState } from 'react';

const ArtifactsPage: React.FC = () => {
  const { formatMessage } = useIntl();
  const { message } = App.useApp();
  const access = useAccess();
  const actionRef = useRef<ActionType>();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [detail, setDetail] = useState<API.ArtifactOut | null>(null);
  const [restoreOpen, setRestoreOpen] = useState(false);
  const [drillOpen, setDrillOpen] = useState(false);
  const [restoreForm] = Form.useForm();
  const [drillForm] = Form.useForm();

  const openDetail = async (id: string) => {
    const row = await request<API.ArtifactOut>(`/api/v1/artifacts/${id}`);
    setDetail(row);
    setDrawerOpen(true);
  };

  const columns: ProColumns<API.ArtifactOut>[] = useMemo(
    () => [
      { title: formatMessage({ id: 'page.artifacts.colCreated' }), dataIndex: 'created_at', valueType: 'dateTime', width: 170 },
      {
        title: formatMessage({ id: 'page.artifacts.colSize' }),
        dataIndex: 'size_bytes',
        width: 120,
        render: (_, r) => {
          const b = r.size_bytes;
          if (b >= 1073741824) return `${(b / 1073741824).toFixed(2)} GiB`;
          if (b >= 1048576) return `${(b / 1048576).toFixed(2)} MiB`;
          if (b >= 1024) return `${(b / 1024).toFixed(1)} KiB`;
          return `${b} B`;
        },
      },
      {
        title: formatMessage({ id: 'page.artifacts.colEncrypted' }),
        dataIndex: 'encrypted',
        width: 72,
        render: (_, r) => (r.encrypted ? formatMessage({ id: 'page.artifacts.yes' }) : formatMessage({ id: 'page.artifacts.no' })),
      },
      {
        title: formatMessage({ id: 'page.artifacts.colLegalHold' }),
        dataIndex: 'legal_hold',
        width: 100,
        render: (_, r) =>
          r.legal_hold ? (
            <Tag color="red">{formatMessage({ id: 'page.artifacts.yes' })}</Tag>
          ) : (
            <Tag>{formatMessage({ id: 'page.artifacts.no' })}</Tag>
          ),
      },
      { title: formatMessage({ id: 'page.artifacts.colChecksum' }), dataIndex: 'checksum_sha256', ellipsis: true, copyable: true },
      {
        title: formatMessage({ id: 'page.artifacts.colActions' }),
        valueType: 'option',
        width: 280,
        render: (_, row) => (
          <Space wrap>
            <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => void openDetail(row.id)}>
              {formatMessage({ id: 'page.artifacts.detail' })}
            </Button>
            {access.canWrite ? (
              <>
                <Button
                  type="link"
                  size="small"
                  onClick={() => {
                    restoreForm.setFieldsValue({
                      artifact_id: row.id,
                      target_path: '',
                      confirm: '',
                      overwrite: false,
                    });
                    setRestoreOpen(true);
                  }}
                >
                  {formatMessage({ id: 'page.artifacts.restore' })}
                </Button>
                <Button
                  type="link"
                  size="small"
                  onClick={() => {
                    drillForm.setFieldsValue({
                      artifact_id: row.id,
                      drill_base_path: '',
                      confirm: '',
                    });
                    setDrillOpen(true);
                  }}
                >
                  {formatMessage({ id: 'page.artifacts.drill' })}
                </Button>
              </>
            ) : null}
          </Space>
        ),
      },
    ],
    [access.canWrite, drillForm, formatMessage, restoreForm],
  );

  const patchLegalHold = async (next: boolean) => {
    if (!detail) return;
    await request(`/api/v1/artifacts/${detail.id}/legal-hold`, {
      method: 'PATCH',
      data: { legal_hold: next },
    });
    message.success(formatMessage({ id: 'page.artifacts.legalHoldUpdated' }));
    const row = await request<API.ArtifactOut>(`/api/v1/artifacts/${detail.id}`);
    setDetail(row);
    actionRef.current?.reload();
  };

  return (
    <PageContainer title={formatMessage({ id: 'page.artifacts.title' })}>
      <Typography.Paragraph type="secondary">{formatMessage({ id: 'page.artifacts.intro' })}</Typography.Paragraph>
      <ProTable<API.ArtifactOut>
        rowKey="id"
        actionRef={actionRef}
        columns={columns}
        search={false}
        request={async (params) => {
          const pageSize = params.pageSize ?? 50;
          const current = params.current ?? 1;
          const offset = (current - 1) * pageSize;
          const rows = await request<API.ArtifactOut[]>('/api/v1/artifacts', {
            params: { limit: pageSize, offset },
          });
          const hasMore = rows.length === pageSize;
          return {
            data: rows,
            success: true,
            total: hasMore ? offset + rows.length + 1 : offset + rows.length,
          };
        }}
        pagination={{ pageSize: 50, showSizeChanger: true }}
      />

      <Drawer
        title={
          detail
            ? formatMessage({ id: 'page.artifacts.drawerTitle' }, { artifactId: detail.id })
            : formatMessage({ id: 'page.artifacts.detail' })
        }
        width={640}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        destroyOnClose
      >
        {detail ? (
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            {access.canAdmin ? (
              <div>
                <Typography.Text strong>{formatMessage({ id: 'page.artifacts.legalHold' })}</Typography.Text>
                <div style={{ marginTop: 8 }}>
                  <Switch
                    checked={detail.legal_hold}
                    onChange={(checked) => {
                      Modal.confirm({
                        title: checked
                          ? formatMessage({ id: 'page.artifacts.legalHoldOn' })
                          : formatMessage({ id: 'page.artifacts.legalHoldOff' }),
                        onOk: () => patchLegalHold(checked),
                      });
                    }}
                  />
                </div>
              </div>
            ) : null}
            <pre style={{ fontSize: 12, background: '#f5f5f5', padding: 12, borderRadius: 8, overflow: 'auto' }}>
              {JSON.stringify(detail, null, 2)}
            </pre>
          </Space>
        ) : null}
      </Drawer>

      <Modal
        title={formatMessage({ id: 'page.artifacts.restoreModalTitle' })}
        open={restoreOpen}
        onCancel={() => setRestoreOpen(false)}
        okText={formatMessage({ id: 'page.artifacts.restoreOk' })}
        onOk={async () => {
          const v = await restoreForm.validateFields();
          if (String(v.confirm).trim() !== 'RESTORE') {
            message.error(formatMessage({ id: 'page.artifacts.restoreConfirmErr' }));
            throw new Error('confirm');
          }
          await request('/api/v1/jobs/restore', {
            method: 'POST',
            data: {
              artifact_id: v.artifact_id,
              target_path: v.target_path,
              confirm_overwrite_non_empty: Boolean(v.overwrite),
            },
          });
          message.success(formatMessage({ id: 'page.artifacts.restoreQueued' }));
          setRestoreOpen(false);
          restoreForm.resetFields();
        }}
        destroyOnClose
        width={520}
      >
        <Form form={restoreForm} layout="vertical">
          <Form.Item name="artifact_id" hidden>
            <Input />
          </Form.Item>
          <Form.Item
            name="target_path"
            label={formatMessage({ id: 'page.artifacts.restoreTarget' })}
            rules={[{ required: true, message: formatMessage({ id: 'page.artifacts.restoreTargetRequired' }) }]}
          >
            <Input placeholder="/restore/here" />
          </Form.Item>
          <Form.Item name="overwrite" label={formatMessage({ id: 'page.artifacts.restoreOverwrite' })} valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item
            name="confirm"
            label={formatMessage({ id: 'page.artifacts.restoreTypeConfirm' })}
            rules={[{ required: true, message: formatMessage({ id: 'page.artifacts.requiredField' }) }]}
          >
            <Input autoComplete="off" placeholder="RESTORE" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={formatMessage({ id: 'page.artifacts.drillModalTitle' })}
        open={drillOpen}
        onCancel={() => setDrillOpen(false)}
        okText={formatMessage({ id: 'page.artifacts.drillOk' })}
        onOk={async () => {
          const v = await drillForm.validateFields();
          if (String(v.confirm).trim() !== 'DRILL') {
            message.error(formatMessage({ id: 'page.artifacts.drillConfirmErr' }));
            throw new Error('confirm');
          }
          await request('/api/v1/jobs/restore-drill', {
            method: 'POST',
            data: {
              artifact_id: v.artifact_id,
              drill_base_path: v.drill_base_path,
            },
          });
          message.success(formatMessage({ id: 'page.artifacts.drillQueued' }));
          setDrillOpen(false);
          drillForm.resetFields();
        }}
        destroyOnClose
        width={520}
      >
        <Form form={drillForm} layout="vertical">
          <Form.Item name="artifact_id" hidden>
            <Input />
          </Form.Item>
          <Form.Item name="drill_base_path" label={formatMessage({ id: 'page.artifacts.drillPathLabel' })} rules={[{ required: true }]}>
            <Input placeholder="/var/tmp/devault-drills" />
          </Form.Item>
          <Form.Item
            name="confirm"
            label={formatMessage({ id: 'page.artifacts.drillConfirm' })}
            rules={[{ required: true, message: formatMessage({ id: 'page.artifacts.requiredField' }) }]}
          >
            <Input autoComplete="off" placeholder="DRILL" />
          </Form.Item>
        </Form>
      </Modal>
    </PageContainer>
  );
};

export default ArtifactsPage;
