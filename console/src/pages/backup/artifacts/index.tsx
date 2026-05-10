import { EyeOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { request, useAccess } from '@umijs/max';
import {
  App,
  Button,
  Drawer,
  Form,
  Input,
  Modal,
  Space,
  Switch,
  Tag,
  Typography,
} from 'antd';
import React, { useRef, useState } from 'react';

const ArtifactsPage: React.FC = () => {
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

  const columns: ProColumns<API.ArtifactOut>[] = [
    { title: '创建时间', dataIndex: 'created_at', valueType: 'dateTime', width: 170 },
    {
      title: '大小',
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
    { title: '加密', dataIndex: 'encrypted', width: 72, render: (_, r) => (r.encrypted ? '是' : '否') },
    {
      title: 'Legal hold',
      dataIndex: 'legal_hold',
      width: 100,
      render: (_, r) => (r.legal_hold ? <Tag color="red">是</Tag> : <Tag>否</Tag>),
    },
    { title: 'SHA256', dataIndex: 'checksum_sha256', ellipsis: true, copyable: true },
    {
      title: '操作',
      valueType: 'option',
      width: 280,
      render: (_, row) => (
        <Space wrap>
          <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => void openDetail(row.id)}>
            详情
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
                恢复
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
                恢复演练
              </Button>
            </>
          ) : null}
        </Space>
      ),
    },
  ];

  const patchLegalHold = async (next: boolean) => {
    if (!detail) return;
    await request(`/api/v1/artifacts/${detail.id}/legal-hold`, {
      method: 'PATCH',
      data: { legal_hold: next },
    });
    message.success('已更新 Legal hold');
    const row = await request<API.ArtifactOut>(`/api/v1/artifacts/${detail.id}`);
    setDetail(row);
    actionRef.current?.reload();
  };

  return (
    <PageContainer title="制品">
      <Typography.Paragraph type="secondary">
        列表使用 <code>limit</code> / <code>offset</code> 分页；恢复与演练为危险操作，需二次确认文案。
      </Typography.Paragraph>
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
        title={detail ? `制品 ${detail.id}` : '详情'}
        width={640}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        destroyOnClose
      >
        {detail ? (
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            {access.canAdmin ? (
              <div>
                <Typography.Text strong>Legal hold（管理员）</Typography.Text>
                <div style={{ marginTop: 8 }}>
                  <Switch
                    checked={detail.legal_hold}
                    onChange={(checked) => {
                      Modal.confirm({
                        title: checked ? '启用 Legal hold？' : '解除 Legal hold？',
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
        title="发起恢复作业"
        open={restoreOpen}
        onCancel={() => setRestoreOpen(false)}
        okText="确认入队"
        onOk={async () => {
          const v = await restoreForm.validateFields();
          if (String(v.confirm).trim() !== 'RESTORE') {
            message.error('请在确认框输入 RESTORE（大写）');
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
          message.success('已入队恢复作业');
          setRestoreOpen(false);
          restoreForm.resetFields();
        }}
        destroyOnClose
        width={520}
      >
        <Form form={restoreForm} layout="vertical">
          <Form.Item name="artifact_id" label="artifact_id" hidden>
            <Input />
          </Form.Item>
          <Form.Item
            name="target_path"
            label="目标绝对目录 target_path"
            rules={[{ required: true, message: '必填' }]}
          >
            <Input placeholder="/restore/here" />
          </Form.Item>
          <Form.Item name="overwrite" label="允许覆盖非空目录" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item
            name="confirm"
            label='确认：输入大写 "RESTORE"'
            rules={[{ required: true, message: '必填' }]}
          >
            <Input autoComplete="off" placeholder="RESTORE" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="发起恢复演练作业"
        open={drillOpen}
        onCancel={() => setDrillOpen(false)}
        okText="确认入队"
        onOk={async () => {
          const v = await drillForm.validateFields();
          if (String(v.confirm).trim() !== 'DRILL') {
            message.error('请在确认框输入 DRILL（大写）');
            throw new Error('confirm');
          }
          await request('/api/v1/jobs/restore-drill', {
            method: 'POST',
            data: {
              artifact_id: v.artifact_id,
              drill_base_path: v.drill_base_path,
            },
          });
          message.success('已入队恢复演练作业');
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
          <Form.Item
            name="drill_base_path"
            label="Agent 上绝对路径前缀 drill_base_path"
            rules={[{ required: true }]}
          >
            <Input placeholder="/var/tmp/devault-drills" />
          </Form.Item>
          <Form.Item
            name="confirm"
            label='确认：输入大写 "DRILL"'
            rules={[{ required: true }]}
          >
            <Input autoComplete="off" placeholder="DRILL" />
          </Form.Item>
        </Form>
      </Modal>
    </PageContainer>
  );
};

export default ArtifactsPage;
