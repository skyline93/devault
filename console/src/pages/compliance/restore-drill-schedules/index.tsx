import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { request, useAccess, useIntl } from '@umijs/max';
import { App, Button, Form, Input, Modal, Select, Space, Switch } from 'antd';
import React, { useEffect, useMemo, useRef, useState } from 'react';

const RestoreDrillSchedulesPage: React.FC = () => {
  const { formatMessage } = useIntl();
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

  const columns: ProColumns<API.RestoreDrillScheduleOut>[] = useMemo(
    () => [
      { title: formatMessage({ id: 'page.drillSchedules.colArtifact' }), dataIndex: 'artifact_id', ellipsis: true, copyable: true },
      { title: formatMessage({ id: 'page.drillSchedules.colCron' }), dataIndex: 'cron_expression', copyable: true },
      { title: formatMessage({ id: 'page.drillSchedules.colTimezone' }), dataIndex: 'timezone', width: 120 },
      { title: formatMessage({ id: 'page.drillSchedules.colPath' }), dataIndex: 'drill_base_path', ellipsis: true },
      {
        title: formatMessage({ id: 'page.drillSchedules.colEnabled' }),
        dataIndex: 'enabled',
        width: 72,
        render: (_, r) =>
          r.enabled ? formatMessage({ id: 'page.drillSchedules.yes' }) : formatMessage({ id: 'page.drillSchedules.no' }),
      },
      {
        title: formatMessage({ id: 'page.drillSchedules.colActions' }),
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
                  {formatMessage({ id: 'page.drillSchedules.edit' })}
                </Button>
                <Button
                  type="link"
                  size="small"
                  danger
                  onClick={() => {
                    Modal.confirm({
                      title: formatMessage({ id: 'page.drillSchedules.deleteTitle' }),
                      onOk: async () => {
                        await request(`/api/v1/restore-drill-schedules/${row.id}`, { method: 'DELETE' });
                        message.success(formatMessage({ id: 'page.drillSchedules.deleted' }));
                        actionRef.current?.reload();
                      },
                    });
                  }}
                >
                  {formatMessage({ id: 'page.drillSchedules.delete' })}
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
      title={formatMessage({ id: 'page.drillSchedules.title' })}
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
            {formatMessage({ id: 'page.drillSchedules.new' })}
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
        title={editRow ? formatMessage({ id: 'page.drillSchedules.modalEdit' }) : formatMessage({ id: 'page.drillSchedules.modalNew' })}
        open={open}
        onCancel={() => setOpen(false)}
        okText={formatMessage({ id: 'page.drillSchedules.okSave' })}
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
            message.success(formatMessage({ id: 'page.drillSchedules.saved' }));
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
            message.success(formatMessage({ id: 'page.drillSchedules.created' }));
          }
          setOpen(false);
          actionRef.current?.reload();
        }}
        destroyOnClose
        width={560}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="artifact_id" label={formatMessage({ id: 'page.drillSchedules.artifact' })} rules={[{ required: true }]}>
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
          <Form.Item name="cron_expression" label={formatMessage({ id: 'page.drillSchedules.colCron' })} rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="timezone" label={formatMessage({ id: 'page.drillSchedules.colTimezone' })}>
            <Input />
          </Form.Item>
          <Form.Item name="drill_base_path" label={formatMessage({ id: 'page.drillSchedules.pathLabel' })} rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="enabled" label={formatMessage({ id: 'page.drillSchedules.colEnabled' })} valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </PageContainer>
  );
};

export default RestoreDrillSchedulesPage;
