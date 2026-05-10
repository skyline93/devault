import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Link, request, useAccess } from '@umijs/max';
import { App, Button, Form, Input, Modal, Select, Space, Switch } from 'antd';
import React, { useEffect, useRef, useState } from 'react';

const SchedulesPage: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
  const actionRef = useRef<ActionType>();
  const [policies, setPolicies] = useState<API.PolicyOut[]>([]);
  const [open, setOpen] = useState(false);
  const [editRow, setEditRow] = useState<API.ScheduleOut | null>(null);
  const [form] = Form.useForm();

  useEffect(() => {
    void request<API.PolicyOut[]>('/api/v1/policies').then(setPolicies);
  }, []);

  const columns: ProColumns<API.ScheduleOut>[] = [
    {
      title: '策略',
      dataIndex: 'policy_id',
      ellipsis: true,
      render: (_, r) => <Link to={`/backup/policies/${r.policy_id}`}>{r.policy_id}</Link>,
    },
    { title: 'Cron', dataIndex: 'cron_expression', copyable: true },
    { title: '时区', dataIndex: 'timezone', width: 140 },
    { title: '启用', dataIndex: 'enabled', width: 72, render: (_, r) => (r.enabled ? '是' : '否') },
    { title: '创建时间', dataIndex: 'created_at', valueType: 'dateTime', width: 170 },
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
                    title: '删除该计划？',
                    onOk: async () => {
                      await request(`/api/v1/schedules/${row.id}`, { method: 'DELETE' });
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
      title="备份计划"
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
      <ProTable<API.ScheduleOut>
        rowKey="id"
        actionRef={actionRef}
        columns={columns}
        search={false}
        request={async () => {
          const data = await request<API.ScheduleOut[]>('/api/v1/schedules');
          return { data, success: true, total: data.length };
        }}
        pagination={{ pageSize: 20 }}
      />

      <Modal
        title={editRow ? '编辑计划' : '新建计划'}
        open={open}
        onCancel={() => setOpen(false)}
        okText="保存"
        onOk={async () => {
          const v = await form.validateFields();
          if (editRow) {
            await request(`/api/v1/schedules/${editRow.id}`, {
              method: 'PATCH',
              data: {
                cron_expression: v.cron_expression,
                timezone: v.timezone,
                enabled: v.enabled,
              },
            });
            message.success('已更新');
          } else {
            await request('/api/v1/schedules', {
              method: 'POST',
              data: {
                policy_id: v.policy_id,
                cron_expression: v.cron_expression,
                timezone: v.timezone || 'UTC',
                enabled: v.enabled !== false,
              },
            });
            message.success('已创建');
          }
          setOpen(false);
          actionRef.current?.reload();
        }}
        destroyOnClose
        width={520}
      >
        <Form form={form} layout="vertical">
          {!editRow ? (
            <Form.Item name="policy_id" label="策略" rules={[{ required: true }]}>
              <Select
                showSearch
                optionFilterProp="label"
                options={policies.map((p) => ({
                  value: p.id,
                  label: `${p.name} (${p.id})`,
                }))}
              />
            </Form.Item>
          ) : null}
          <Form.Item name="cron_expression" label="Cron" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="timezone" label="时区">
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

export default SchedulesPage;
