import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { ProTable } from '@ant-design/pro-components';
import { request, useAccess, useIntl } from '@umijs/max';
import { App, Button, Drawer, Form, Input, Modal, Space, Spin, Switch, Tag } from 'antd';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import PolicyFormFields from './PolicyFormFields';
import { buildConfigPayloadFromValues, parseConfig, type PolicyPluginKind } from './policyPayload';

export type PolicyEditDrawerProps = {
  open: boolean;
  policyId: string | undefined;
  onClose: () => void;
  onSaved: () => void;
};

const PolicyEditDrawer: React.FC<PolicyEditDrawerProps> = ({ open, policyId, onClose, onSaved }) => {
  const { formatMessage } = useIntl();
  const { message } = App.useApp();
  const access = useAccess();
  const [form] = Form.useForm();
  const pluginKind = (Form.useWatch('policy_plugin', form) as PolicyPluginKind) ?? 'file';
  const [loading, setLoading] = useState(false);
  const [schedules, setSchedules] = useState<API.ScheduleOut[]>([]);
  const [tenantAgents, setTenantAgents] = useState<API.TenantScopedAgentOut[]>([]);
  const scheduleRef = useRef<ActionType>();
  const [schOpen, setSchOpen] = useState(false);
  const [schForm] = Form.useForm();
  const [editSchOpen, setEditSchOpen] = useState(false);
  const [editSchForm] = Form.useForm();
  const [editingScheduleId, setEditingScheduleId] = useState<string | undefined>();
  const [enablingScheduleId, setEnablingScheduleId] = useState<string | undefined>();

  const loadAux = useCallback(async () => {
    const [sch, ta] = await Promise.all([
      request<API.ScheduleOut[]>('/api/v1/schedules'),
      request<API.TenantScopedAgentOut[]>('/api/v1/tenant-agents'),
    ]);
    setSchedules(sch);
    setTenantAgents(ta);
  }, []);

  const loadPolicy = useCallback(async () => {
    if (!policyId) return;
    setLoading(true);
    try {
      const p = await request<API.PolicyOut>(`/api/v1/policies/${policyId}`);
      const pl = p.plugin === 'postgres_pgbackrest' ? 'postgres_pgbackrest' : 'file';
      form.setFieldsValue({
        name: p.name,
        policy_plugin: pl,
        ...parseConfig(p.config as Record<string, unknown> | undefined, pl),
        bound_agent_id: p.bound_agent_id ?? undefined,
      });
    } finally {
      setLoading(false);
    }
  }, [policyId, form]);

  useEffect(() => {
    if (!open || !policyId) return;
    void loadAux();
    void loadPolicy();
  }, [open, policyId, loadAux, loadPolicy]);

  const filteredSchedules = useMemo(() => {
    if (!policyId) return [];
    return schedules.filter((s) => s.policy_id === policyId);
  }, [schedules, policyId]);

  const openEditSchedule = useCallback(
    (row: API.ScheduleOut) => {
      setEditingScheduleId(row.id);
      editSchForm.setFieldsValue({
        cron_expression: row.cron_expression,
        timezone: row.timezone || 'UTC',
      });
      setEditSchOpen(true);
    },
    [editSchForm],
  );

  const schColumns: ProColumns<API.ScheduleOut>[] = useMemo(
    () => [
      {
        title: formatMessage({ id: 'page.schedules.colCron' }),
        dataIndex: 'cron_expression',
        copyable: true,
      },
      {
        title: formatMessage({ id: 'page.schedules.colTimezone' }),
        dataIndex: 'timezone',
        width: 140,
      },
      {
        title: formatMessage({ id: 'page.schedules.colActions' }),
        valueType: 'option',
        width: 280,
        render: (_, row) => (
          <Space size="small" wrap align="center">
            {access.canWrite ? (
              <Switch
                checked={row.enabled}
                loading={enablingScheduleId === row.id}
                onChange={(checked) => {
                  if (checked === row.enabled) return;
                  Modal.confirm({
                    title: checked
                      ? formatMessage({ id: 'page.policyEdit.scheduleEnableConfirmTitle' })
                      : formatMessage({ id: 'page.policyEdit.scheduleDisableConfirmTitle' }),
                    content: checked
                      ? formatMessage({ id: 'page.policyEdit.scheduleEnableConfirmContent' })
                      : formatMessage({ id: 'page.policyEdit.scheduleDisableConfirmContent' }),
                    onOk: async () => {
                      setEnablingScheduleId(row.id);
                      try {
                        await request(`/api/v1/schedules/${row.id}`, {
                          method: 'PATCH',
                          data: { enabled: checked },
                        });
                        message.success(formatMessage({ id: 'page.policyEdit.scheduleEnablementUpdated' }));
                        await loadAux();
                        scheduleRef.current?.reload();
                      } catch {
                        message.error(formatMessage({ id: 'page.policyEdit.scheduleEnablementUpdateFailed' }));
                      } finally {
                        setEnablingScheduleId(undefined);
                      }
                    },
                  });
                }}
              />
            ) : row.enabled ? (
              <Tag color="green">{formatMessage({ id: 'page.schedules.yes' })}</Tag>
            ) : (
              <Tag>{formatMessage({ id: 'page.schedules.no' })}</Tag>
            )}
            {access.canWrite ? (
              <Button type="link" size="small" onClick={() => openEditSchedule(row)}>
                {formatMessage({ id: 'page.policyEdit.editSchedule' })}
              </Button>
            ) : null}
            {access.canWrite ? (
              <Button
                type="link"
                size="small"
                danger
                onClick={() => {
                  Modal.confirm({
                    title: formatMessage({ id: 'page.policyEdit.deleteScheduleTitle' }),
                    onOk: async () => {
                      await request(`/api/v1/schedules/${row.id}`, { method: 'DELETE' });
                      message.success(formatMessage({ id: 'page.policyEdit.scheduleDeleted' }));
                      await loadAux();
                      scheduleRef.current?.reload();
                    },
                  });
                }}
              >
                {formatMessage({ id: 'page.schedules.delete' })}
              </Button>
            ) : null}
          </Space>
        ),
      },
    ],
    [access.canWrite, enablingScheduleId, formatMessage, loadAux, message, openEditSchedule],
  );

  const onSave = async () => {
    if (!policyId) return;
    try {
      const values = await form.validateFields();
      const pl = (values.policy_plugin as PolicyPluginKind) || 'file';
      const config = buildConfigPayloadFromValues(values, pl);
      await request(`/api/v1/policies/${policyId}`, {
        method: 'PATCH',
        data: {
          name: values.name,
          config,
        },
      });
      message.success(formatMessage({ id: 'page.policyEdit.policySaved' }));
      onSaved();
      await loadPolicy();
      await loadAux();
    } catch (e: unknown) {
      const err = e as { errorFields?: unknown };
      if (err?.errorFields) return;
      message.error(formatMessage({ id: 'page.policyEdit.policySaveFailed' }));
    }
  };

  const closeEditScheduleModal = () => {
    setEditSchOpen(false);
    setEditingScheduleId(undefined);
    editSchForm.resetFields();
  };

  return (
    <Drawer
      title={formatMessage({ id: 'page.policyEdit.editTitle' })}
      width={720}
      open={open}
      onClose={onClose}
      destroyOnClose
    >
      <Spin spinning={loading}>
        <Form form={form} layout="vertical" disabled={!access.canWrite}>
          <PolicyFormFields tenantAgents={tenantAgents} pathsAgentDisabled pluginKind={pluginKind} pluginLocked />
          {access.canWrite ? (
            <Button type="primary" onClick={() => void onSave()} style={{ marginTop: 16 }}>
              {formatMessage({ id: 'page.policyEdit.save' })}
            </Button>
          ) : null}
        </Form>

        {policyId ? (
          <div style={{ marginTop: 24 }}>
            <div style={{ fontWeight: 600, marginBottom: 12 }}>{formatMessage({ id: 'page.policyEdit.schedulesCard' })}</div>
            {access.canWrite ? (
              <Button type="primary" onClick={() => setSchOpen(true)} style={{ marginBottom: 12 }}>
                {formatMessage({ id: 'page.policyEdit.newSchedule' })}
              </Button>
            ) : null}
            <ProTable<API.ScheduleOut>
              rowKey="id"
              actionRef={scheduleRef}
              search={false}
              columns={schColumns}
              dataSource={filteredSchedules}
              pagination={false}
              toolBarRender={false}
            />
          </div>
        ) : null}
      </Spin>

      <Modal
        title={formatMessage({ id: 'page.policyEdit.scheduleModalNew' })}
        open={schOpen}
        onCancel={() => setSchOpen(false)}
        onOk={async () => {
          const v = await schForm.validateFields();
          await request('/api/v1/schedules', {
            method: 'POST',
            data: {
              policy_id: policyId,
              cron_expression: v.cron_expression,
              timezone: v.timezone || 'UTC',
              enabled: v.enabled !== false,
            },
          });
          message.success(formatMessage({ id: 'page.policyEdit.scheduleCreated' }));
          schForm.resetFields();
          setSchOpen(false);
          await loadAux();
          scheduleRef.current?.reload();
        }}
        destroyOnClose
      >
        <Form form={schForm} layout="vertical">
          <Form.Item name="cron_expression" label={formatMessage({ id: 'page.policyEdit.cron' })} rules={[{ required: true }]}>
            <Input placeholder="0 2 * * *" />
          </Form.Item>
          <Form.Item name="timezone" label={formatMessage({ id: 'page.policyEdit.timezone' })} initialValue="UTC">
            <Input />
          </Form.Item>
          <Form.Item name="enabled" label={formatMessage({ id: 'page.policyEdit.scheduleEnabled' })} valuePropName="checked" initialValue>
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={formatMessage({ id: 'page.policyEdit.scheduleModalEdit' })}
        open={editSchOpen}
        onCancel={closeEditScheduleModal}
        destroyOnClose
        onOk={async () => {
          if (!editingScheduleId) return;
          try {
            const v = await editSchForm.validateFields();
            await request(`/api/v1/schedules/${editingScheduleId}`, {
              method: 'PATCH',
              data: {
                cron_expression: v.cron_expression,
                timezone: (v.timezone as string)?.trim() || 'UTC',
              },
            });
            message.success(formatMessage({ id: 'page.policyEdit.scheduleUpdated' }));
            closeEditScheduleModal();
            await loadAux();
            scheduleRef.current?.reload();
          } catch (e: unknown) {
            const err = e as { errorFields?: unknown };
            if (err?.errorFields) return;
            message.error(formatMessage({ id: 'page.policyEdit.scheduleUpdateFailed' }));
          }
        }}
      >
        <Form form={editSchForm} layout="vertical">
          <Form.Item name="cron_expression" label={formatMessage({ id: 'page.policyEdit.cron' })} rules={[{ required: true }]}>
            <Input placeholder="0 2 * * *" />
          </Form.Item>
          <Form.Item name="timezone" label={formatMessage({ id: 'page.policyEdit.timezone' })}>
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </Drawer>
  );
};

export default PolicyEditDrawer;
