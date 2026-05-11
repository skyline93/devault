import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Link, request, useAccess, useIntl } from '@umijs/max';
import { App, Button, Form, Input, Modal, Select, Space, Switch } from 'antd';
import React, { useEffect, useMemo, useRef, useState } from 'react';

const SchedulesPage: React.FC = () => {
  const { formatMessage } = useIntl();
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

  const columns: ProColumns<API.ScheduleOut>[] = useMemo(
    () => [
      {
        title: formatMessage({ id: 'page.schedules.colPolicy' }),
        dataIndex: 'policy_id',
        ellipsis: true,
        render: (_, r) => <Link to={`/backup/policies/${r.policy_id}`}>{r.policy_id}</Link>,
      },
      { title: formatMessage({ id: 'page.schedules.colCron' }), dataIndex: 'cron_expression', copyable: true },
      { title: formatMessage({ id: 'page.schedules.colTimezone' }), dataIndex: 'timezone', width: 140 },
      {
        title: formatMessage({ id: 'page.schedules.colEnabled' }),
        dataIndex: 'enabled',
        width: 72,
        render: (_, r) => (r.enabled ? formatMessage({ id: 'page.schedules.yes' }) : formatMessage({ id: 'page.schedules.no' })),
      },
      { title: formatMessage({ id: 'page.schedules.colCreated' }), dataIndex: 'created_at', valueType: 'dateTime', width: 170 },
      {
        title: formatMessage({ id: 'page.schedules.colActions' }),
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
                  {formatMessage({ id: 'page.schedules.edit' })}
                </Button>
                <Button
                  type="link"
                  size="small"
                  danger
                  onClick={() => {
                    Modal.confirm({
                      title: formatMessage({ id: 'page.schedules.deleteTitle' }),
                      onOk: async () => {
                        await request(`/api/v1/schedules/${row.id}`, { method: 'DELETE' });
                        message.success(formatMessage({ id: 'page.schedules.deleted' }));
                        actionRef.current?.reload();
                      },
                    });
                  }}
                >
                  {formatMessage({ id: 'page.schedules.delete' })}
                </Button>
              </>
            ) : null}
          </Space>
        ),
      },
    ],
    [access.canWrite, formatMessage, form, message],
  );

  return (
    <PageContainer
      title={formatMessage({ id: 'page.schedules.title' })}
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
            {formatMessage({ id: 'page.schedules.new' })}
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
        title={editRow ? formatMessage({ id: 'page.schedules.modalEdit' }) : formatMessage({ id: 'page.schedules.modalNew' })}
        open={open}
        onCancel={() => setOpen(false)}
        okText={formatMessage({ id: 'page.schedules.okSave' })}
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
            message.success(formatMessage({ id: 'page.schedules.saved' }));
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
            message.success(formatMessage({ id: 'page.schedules.created' }));
          }
          setOpen(false);
          actionRef.current?.reload();
        }}
        destroyOnClose
        width={520}
      >
        <Form form={form} layout="vertical">
          {!editRow ? (
            <Form.Item name="policy_id" label={formatMessage({ id: 'page.schedules.policy' })} rules={[{ required: true }]}>
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
          <Form.Item name="cron_expression" label={formatMessage({ id: 'page.schedules.colCron' })} rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="timezone" label={formatMessage({ id: 'page.schedules.colTimezone' })}>
            <Input />
          </Form.Item>
          <Form.Item name="enabled" label={formatMessage({ id: 'page.schedules.colEnabled' })} valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </PageContainer>
  );
};

export default SchedulesPage;
