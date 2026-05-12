import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { history, Link, request, useAccess, useIntl, useLocation } from '@umijs/max';
import {
  App,
  Button,
  Card,
  Form,
  Input,
  InputNumber,
  Modal,
  Select,
  Space,
  Switch,
  Tabs,
} from 'antd';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';

function parseConfig(raw: Record<string, unknown> | undefined) {
  const c = raw ?? {};
  const paths = Array.isArray(c.paths) ? (c.paths as string[]).join('\n') : '';
  const excludes = Array.isArray(c.excludes) ? (c.excludes as string[]).join('\n') : '';
  return {
    pathsText: paths,
    excludesText: excludes,
    follow_symlinks: Boolean(c.follow_symlinks),
    preserve_uid_gid: c.preserve_uid_gid !== false,
    one_filesystem: Boolean(c.one_filesystem),
    encrypt_artifacts: Boolean(c.encrypt_artifacts),
    kms_envelope_key_id: (c.kms_envelope_key_id as string) || undefined,
    object_lock_mode: (c.object_lock_mode as string) || undefined,
    object_lock_retain_days: c.object_lock_retain_days as number | undefined,
    retention_days: c.retention_days as number | undefined,
  };
}

const PolicyEditPage: React.FC = () => {
  const { formatMessage } = useIntl();
  const { message } = App.useApp();
  const access = useAccess();
  const { pathname } = useLocation();
  const isNew = pathname.endsWith('/new');
  const policyId = isNew ? undefined : pathname.split('/').pop();

  const [form] = Form.useForm();
  const [loading, setLoading] = useState(!isNew);
  const [schedules, setSchedules] = useState<API.ScheduleOut[]>([]);
  const [tenantAgents, setTenantAgents] = useState<API.TenantScopedAgentOut[]>([]);
  const scheduleRef = useRef<ActionType>();
  const [schOpen, setSchOpen] = useState(false);
  const [schForm] = Form.useForm();

  const loadAux = useCallback(async () => {
    const [sch, ta] = await Promise.all([
      request<API.ScheduleOut[]>('/api/v1/schedules'),
      request<API.TenantScopedAgentOut[]>('/api/v1/tenant-agents'),
    ]);
    setSchedules(sch);
    setTenantAgents(ta);
  }, []);

  useEffect(() => {
    void loadAux();
  }, [loadAux]);

  useEffect(() => {
    if (isNew || !policyId) {
      setLoading(false);
      form.setFieldsValue({
        name: '',
        enabled: true,
        ...parseConfig({ version: 1, paths: [] }),
      });
      return;
    }
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const p = await request<API.PolicyOut>(`/api/v1/policies/${policyId}`);
        if (cancelled) return;
        form.setFieldsValue({
          name: p.name,
          enabled: p.enabled,
          ...parseConfig(p.config),
        });
        form.setFieldValue('bound_agent_id', p.bound_agent_id ?? undefined);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [isNew, policyId, form]);

  const filteredSchedules = useMemo(() => {
    if (!policyId) return [];
    return schedules.filter((s) => s.policy_id === policyId);
  }, [schedules, policyId]);

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
        title: formatMessage({ id: 'page.schedules.colEnabled' }),
        dataIndex: 'enabled',
        width: 72,
        render: (_, r) =>
          r.enabled
            ? formatMessage({ id: 'page.schedules.yes' })
            : formatMessage({ id: 'page.schedules.no' }),
      },
      {
        title: formatMessage({ id: 'page.schedules.colActions' }),
        valueType: 'option',
        width: 200,
        render: (_, row) => (
          <Space>
            <Link to="/compliance/schedules">{formatMessage({ id: 'page.policyEdit.plansLink' })}</Link>
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
    [access.canWrite, formatMessage, loadAux, message],
  );

  const buildConfigPayload = () => {
    const v = form.getFieldsValue();
    const paths = String(v.pathsText || '')
      .split('\n')
      .map((s: string) => s.trim())
      .filter(Boolean);
    const excludes = String(v.excludesText || '')
      .split('\n')
      .map((s: string) => s.trim())
      .filter(Boolean);
    const mode = v.object_lock_mode as string | undefined;
    const days = v.object_lock_retain_days as number | undefined;
    const config: Record<string, unknown> = {
      version: 1,
      paths,
      excludes,
      follow_symlinks: Boolean(v.follow_symlinks),
      preserve_uid_gid: v.preserve_uid_gid !== false,
      one_filesystem: Boolean(v.one_filesystem),
      encrypt_artifacts: Boolean(v.encrypt_artifacts),
    };
    const kms = (v.kms_envelope_key_id as string)?.trim();
    if (kms) config.kms_envelope_key_id = kms;
    if (mode) {
      config.object_lock_mode = mode;
      config.object_lock_retain_days = days;
    }
    const rd = v.retention_days as number | undefined;
    if (rd != null && rd > 0) config.retention_days = rd;
    return config;
  };

  const bindingPayload = () => {
    const v = form.getFieldsValue();
    return { bound_agent_id: v.bound_agent_id as string };
  };

  const onSave = async () => {
    const values = await form.validateFields();
    const config = buildConfigPayload();
    const bind = bindingPayload();

    if (isNew) {
      await request('/api/v1/policies', {
        method: 'POST',
        data: {
          name: values.name,
          plugin: 'file',
          enabled: values.enabled !== false,
          config,
          ...bind,
        },
      });
      message.success(formatMessage({ id: 'page.policyEdit.policyCreated' }));
      history.push('/backup/policies');
      return;
    }
    await request(`/api/v1/policies/${policyId}`, {
      method: 'PATCH',
      data: {
        name: values.name,
        enabled: values.enabled,
        config,
        ...bind,
      },
    });
    message.success(formatMessage({ id: 'page.policyEdit.policySaved' }));
    history.push('/backup/policies');
  };

  return (
    <PageContainer
      title={isNew ? formatMessage({ id: 'page.policyEdit.newTitle' }) : formatMessage({ id: 'page.policyEdit.editTitle' })}
      loading={loading}
      onBack={() => history.push('/backup/policies')}
    >
      <Card>
        <Form form={form} layout="vertical" disabled={!access.canWrite}>
          <Tabs
            items={[
              {
                key: 'basic',
                label: formatMessage({ id: 'page.policyEdit.tabBasic' }),
                children: (
                  <Space direction="vertical" style={{ width: '100%' }} size="middle">
                    <Form.Item
                      name="name"
                      label={formatMessage({ id: 'page.policyEdit.name' })}
                      rules={[{ required: true, message: formatMessage({ id: 'page.policyEdit.nameRequired' }) }]}
                    >
                      <Input maxLength={255} />
                    </Form.Item>
                    <Form.Item
                      name="enabled"
                      label={formatMessage({ id: 'page.policyEdit.enabled' })}
                      valuePropName="checked"
                      initialValue
                    >
                      <Switch />
                    </Form.Item>
                  </Space>
                ),
              },
              {
                key: 'file',
                label: formatMessage({ id: 'page.policyEdit.tabConfig' }),
                children: (
                  <Space direction="vertical" style={{ width: '100%' }} size="middle">
                    <Form.Item
                      name="pathsText"
                      label={formatMessage({ id: 'page.policyEdit.pathsLabel' })}
                      rules={[{ required: true, message: formatMessage({ id: 'page.policyEdit.pathsRequired' }) }]}
                    >
                      <Input.TextArea
                        rows={6}
                        placeholder={formatMessage({ id: 'page.policyEdit.pathsPlaceholder' })}
                      />
                    </Form.Item>
                    <Form.Item
                      name="excludesText"
                      label={formatMessage({ id: 'page.policyEdit.excludesLabel' })}
                    >
                      <Input.TextArea
                        rows={4}
                        placeholder={formatMessage({ id: 'page.policyEdit.excludesPlaceholder' })}
                      />
                    </Form.Item>
                    <Form.Item
                      name="follow_symlinks"
                      label={formatMessage({ id: 'page.policyEdit.followSymlinks' })}
                      valuePropName="checked"
                    >
                      <Switch />
                    </Form.Item>
                    <Form.Item
                      name="preserve_uid_gid"
                      label={formatMessage({ id: 'page.policyEdit.preserveUidGid' })}
                      valuePropName="checked"
                    >
                      <Switch defaultChecked />
                    </Form.Item>
                    <Form.Item
                      name="one_filesystem"
                      label={formatMessage({ id: 'page.policyEdit.oneFilesystem' })}
                      valuePropName="checked"
                    >
                      <Switch />
                    </Form.Item>
                    <Form.Item
                      name="encrypt_artifacts"
                      label={formatMessage({ id: 'page.policyEdit.encryptArtifacts' })}
                      valuePropName="checked"
                    >
                      <Switch />
                    </Form.Item>
                    <Form.Item name="kms_envelope_key_id" label={formatMessage({ id: 'page.policyEdit.kmsLabel' })}>
                      <Input placeholder={formatMessage({ id: 'page.policyEdit.kmsPh' })} />
                    </Form.Item>
                    <Form.Item name="object_lock_mode" label={formatMessage({ id: 'page.policyEdit.retentionMode' })}>
                      <Select
                        allowClear
                        options={[
                          {
                            value: 'GOVERNANCE',
                            label: formatMessage({ id: 'page.policyEdit.objectLockGovernance' }),
                          },
                          {
                            value: 'COMPLIANCE',
                            label: formatMessage({ id: 'page.policyEdit.objectLockCompliance' }),
                          },
                        ]}
                      />
                    </Form.Item>
                    <Form.Item
                      name="object_lock_retain_days"
                      label={formatMessage({ id: 'page.policyEdit.objectLockRetainDays' })}
                    >
                      <InputNumber
                        min={1}
                        style={{ width: '100%' }}
                        placeholder={formatMessage({ id: 'page.policyEdit.objectLockRetainPlaceholder' })}
                      />
                    </Form.Item>
                    <Form.Item name="retention_days" label={formatMessage({ id: 'page.policyEdit.backupRetentionDays' })}>
                      <InputNumber min={1} style={{ width: '100%' }} />
                    </Form.Item>
                  </Space>
                ),
              },
              {
                key: 'bind',
                label: formatMessage({ id: 'page.policyEdit.tabBinding' }),
                children: (
                  <Space direction="vertical" style={{ width: '100%' }} size="middle">
                    <Form.Item
                      name="bound_agent_id"
                      label={formatMessage({ id: 'page.policyEdit.agentLabel' })}
                      rules={[
                        {
                          required: true,
                          message: formatMessage({ id: 'page.policyEdit.agentRequired' }),
                        },
                      ]}
                    >
                      <Select
                        showSearch
                        optionFilterProp="label"
                        options={tenantAgents.map((a) => ({
                          value: a.id,
                          label: `${a.hostname ?? a.id} (${a.id})`,
                        }))}
                      />
                    </Form.Item>
                    <Link to="/execution/tenant-agents">{formatMessage({ id: 'page.policyEdit.agentsLink' })}</Link>
                  </Space>
                ),
              },
            ]}
          />
          {access.canWrite ? (
            <Button type="primary" onClick={() => void onSave()} style={{ marginTop: 16 }}>
              {formatMessage({ id: 'page.policyEdit.save' })}
            </Button>
          ) : null}
        </Form>
      </Card>

      {!isNew && policyId ? (
        <Card title={formatMessage({ id: 'page.policyEdit.schedulesCard' })} style={{ marginTop: 16 }}>
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
        </Card>
      ) : null}

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
          <Form.Item
            name="cron_expression"
            label={formatMessage({ id: 'page.policyEdit.cron' })}
            rules={[{ required: true }]}
          >
            <Input placeholder="0 2 * * *" />
          </Form.Item>
          <Form.Item name="timezone" label={formatMessage({ id: 'page.policyEdit.timezone' })} initialValue="UTC">
            <Input />
          </Form.Item>
          <Form.Item
            name="enabled"
            label={formatMessage({ id: 'page.policyEdit.scheduleEnabled' })}
            valuePropName="checked"
            initialValue
          >
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </PageContainer>
  );
};

export default PolicyEditPage;
