import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { request, useAccess } from '@umijs/max';
import { App, Button, Form, Input, Modal, Select, Space, Switch } from 'antd';
import React, { useEffect, useRef, useState } from 'react';

const RestoreDrillSchedulesPage: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
  const actionRef = useRef<ActionType>();
  const [artifacts, setArtifacts] = useState<API.ArtifactOut[]>([]);
  const [open, setOpen] = useState(false);
  const [editRow, setEditRow] = useState<API.RestoreDrillScheduleOut | null>(null);
  const [form] = Form.useForm();

  const loadArtifacts = async () => {
    const rows = await request<API.ArtifactOut[]>('/api/v1/artifacts', { params: { limit: 200, offset: 0 } });
    setArtifacts(rows);
  };

  useEffect(() => {
    void loadArtifacts();
  }, []);

  const columns: ProColumns<API.RestoreDrillScheduleOut>[] = [
    { title: '制品', dataIndex: 'artifact_id', ellipsis: true, copyable: true },
    { title: 'Cron', dataIndex: 'cron_expression', copyable: true },
    { title: '时区', dataIndex: 'timezone', width: 120 },
    { title: '演练根路径', dataIndex: 'drill_base_path', ellipsis: true },
    { title: '启用', dataIndex: 'enabled', width: 72, render: (_, r) => (r.enabled ? '是' : '否') },
    {
      title: '操作',
      valueType: 'option',
      width: 160,
      render: (_, row) => (
        <Space>
          {access.canWrite ? (
            <>
              <Button
                type="link"
                size="small"
                onClick={() => {
                  setEditRow(row);
                  form.setFieldsValue({
                    cron_expression: row.cron_expression,
                    timezone: row.timezone,
                    enabled: row.enabled,
                    drill_base_path: row.drill_base_path,
                    artifact_id: row.artifact_id,
                  });
                  setOpen(true);
                }}
              >
                编辑
              </Button>
              <Button
                type="link"
                size="small"
                danger
                onClick={() => {
                  Modal.confirm({
                    title: '删除该演练计划？',
                    onOk: async () => {
                      await request(`/api/v1/restore-drill-schedules/${row.id}`, { method: 'DELETE' });
                      message.success('已删除');
                      actionRef.current?.reload();
                    },
                  });
                }}
              >
                删除
              </Button>
            </>
          ) : null}
        </Space>
      ),
    },
  ];

  return (
    <PageContainer
      title="恢复演练计划"
      extra={
        access.canWrite ? (
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              setEditRow(null);
              form.resetFields();
              form.setFieldsValue({ timezone: 'UTC', enabled: true });
              setOpen(true);
            }}
          >
            新建
          </Button>
        ) : undefined
      }
    >
      <ProTable<API.RestoreDrillScheduleOut>
        rowKey="id"
        actionRef={actionRef}
        columns={columns}
        search={false}
        request={async () => {
          const data = await request<API.RestoreDrillScheduleOut[]>('/api/v1/restore-drill-schedules');
          return { data, success: true, total: data.length };
        }}
        pagination={{ pageSize: 20 }}
      />

      <Modal
        title={editRow ? '编辑演练计划' : '新建演练计划'}
        open={open}
        onCancel={() => setOpen(false)}
        okText="保存"
        onOk={async () => {
          const v = await form.validateFields();
          if (editRow) {
            await request(`/api/v1/restore-drill-schedules/${editRow.id}`, {
              method: 'PATCH',
              data: {
                cron_expression: v.cron_expression,
                timezone: v.timezone,
                enabled: v.enabled,
                drill_base_path: v.drill_base_path,
                artifact_id: v.artifact_id,
              },
            });
            message.success('已更新');
          } else {
            await request('/api/v1/restore-drill-schedules', {
              method: 'POST',
              data: {
                artifact_id: v.artifact_id,
                cron_expression: v.cron_expression,
                timezone: v.timezone || 'UTC',
                enabled: v.enabled !== false,
                drill_base_path: v.drill_base_path,
              },
            });
            message.success('已创建');
          }
          setOpen(false);
          actionRef.current?.reload();
        }}
        destroyOnClose
        width={560}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="artifact_id" label="制品" rules={[{ required: true }]}>
            <Select
              showSearch
              optionFilterProp="label"
              disabled={Boolean(editRow)}
              options={artifacts.map((a) => ({
                value: a.id,
                label: `${a.id} · ${a.created_at}`,
              }))}
            />
          </Form.Item>
          <Form.Item name="cron_expression" label="Cron" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="timezone" label="时区">
            <Input />
          </Form.Item>
          <Form.Item name="drill_base_path" label="drill_base_path（绝对路径）" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="enabled" label="启用" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </PageContainer>
  );
};

export default RestoreDrillSchedulesPage;
