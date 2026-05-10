import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { history, Link, request, useAccess, useLocation } from '@umijs/max';
import {
  App,
  Button,
  Card,
  Form,
  Input,
  InputNumber,
  Modal,
  Radio,
  Select,
  Space,
  Switch,
  Tabs,
} from 'antd';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';

type BindingMode = 'none' | 'agent' | 'pool';

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
  const { message } = App.useApp();
  const access = useAccess();
  const { pathname } = useLocation();
  const isNew = pathname.endsWith('/new');
  const policyId = isNew ? undefined : pathname.split('/').pop();

  const [form] = Form.useForm();
  const [loading, setLoading] = useState(!isNew);
  const [bindingMode, setBindingMode] = useState<BindingMode>('none');
  const [schedules, setSchedules] = useState<API.ScheduleOut[]>([]);
  const [pools, setPools] = useState<API.AgentPoolOut[]>([]);
  const [tenantAgents, setTenantAgents] = useState<API.TenantScopedAgentOut[]>([]);
  const scheduleRef = useRef<ActionType>();
  const [schOpen, setSchOpen] = useState(false);
  const [schForm] = Form.useForm();

  const loadAux = useCallback(async () => {
    const [sch, pl, ta] = await Promise.all([
      request<API.ScheduleOut[]>('/api/v1/schedules'),
      request<API.AgentPoolOut[]>('/api/v1/agent-pools'),
      request<API.TenantScopedAgentOut[]>('/api/v1/tenant-agents'),
    ]);
    setSchedules(sch);
    setPools(pl);
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
      setBindingMode('none');
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
        if (p.bound_agent_id) setBindingMode('agent');
        else if (p.bound_agent_pool_id) setBindingMode('pool');
        else setBindingMode('none');
        form.setFieldValue('bound_agent_id', p.bound_agent_id ?? undefined);
        form.setFieldValue('bound_agent_pool_id', p.bound_agent_pool_id ?? undefined);
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

  const schColumns: ProColumns<API.ScheduleOut>[] = [
    { title: 'Cron', dataIndex: 'cron_expression', copyable: true },
    { title: '时区', dataIndex: 'timezone', width: 140 },
    { title: '启用', dataIndex: 'enabled', width: 72, render: (_, r) => (r.enabled ? '是' : '否') },
    {
      title: '操作',
      valueType: 'option',
      width: 160,
      render: (_, row) => (
        <Space>
          <Link to="/compliance/schedules">计划管理</Link>
          {access.canWrite ? (
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
                    await loadAux();
                    scheduleRef.current?.reload();
                  },
                });
              }}
            >
              删除
            </Button>
          ) : null}
        </Space>
      ),
    },
  ];

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
    if (bindingMode === 'agent') {
      return { bound_agent_id: v.bound_agent_id as string, bound_agent_pool_id: null };
    }
    if (bindingMode === 'pool') {
      return { bound_agent_id: null, bound_agent_pool_id: v.bound_agent_pool_id as string };
    }
    return { bound_agent_id: null, bound_agent_pool_id: null };
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
      message.success('已创建');
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
    message.success('已保存');
    history.push('/backup/policies');
  };

  return (
    <PageContainer
      title={isNew ? '新建策略' : '编辑策略'}
      loading={loading}
      onBack={() => history.push('/backup/policies')}
    >
      <Card>
        <Form form={form} layout="vertical" disabled={!access.canWrite}>
          <Tabs
            items={[
              {
                key: 'basic',
                label: '基本',
                children: (
                  <Space direction="vertical" style={{ width: '100%' }} size="middle">
                    <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
                      <Input maxLength={255} />
                    </Form.Item>
                    <Form.Item name="enabled" label="启用" valuePropName="checked" initialValue>
                      <Switch />
                    </Form.Item>
                  </Space>
                ),
              },
              {
                key: 'file',
                label: '文件备份配置 (FileBackupConfigV1)',
                children: (
                  <Space direction="vertical" style={{ width: '100%' }} size="middle">
                    <Form.Item
                      name="pathsText"
                      label="paths（每行一个绝对路径）"
                      rules={[{ required: true, message: '至少一行路径' }]}
                    >
                      <Input.TextArea rows={6} placeholder="/data/app&#10;/var/log" />
                    </Form.Item>
                    <Form.Item name="excludesText" label="excludes（gitwildmatch，每行一条）">
                      <Input.TextArea rows={4} placeholder="**/.git/**" />
                    </Form.Item>
                    <Form.Item name="follow_symlinks" label="follow_symlinks" valuePropName="checked">
                      <Switch />
                    </Form.Item>
                    <Form.Item name="preserve_uid_gid" label="preserve_uid_gid" valuePropName="checked">
                      <Switch defaultChecked />
                    </Form.Item>
                    <Form.Item name="one_filesystem" label="one_filesystem" valuePropName="checked">
                      <Switch />
                    </Form.Item>
                    <Form.Item name="encrypt_artifacts" label="encrypt_artifacts" valuePropName="checked">
                      <Switch />
                    </Form.Item>
                    <Form.Item name="kms_envelope_key_id" label="kms_envelope_key_id（可选）">
                      <Input placeholder="CMK id 或 ARN" />
                    </Form.Item>
                    <Form.Item name="object_lock_mode" label="object_lock_mode">
                      <Select
                        allowClear
                        options={[
                          { value: 'GOVERNANCE', label: 'GOVERNANCE' },
                          { value: 'COMPLIANCE', label: 'COMPLIANCE' },
                        ]}
                      />
                    </Form.Item>
                    <Form.Item name="object_lock_retain_days" label="object_lock_retain_days">
                      <InputNumber min={1} style={{ width: '100%' }} placeholder="与 mode 成对填写" />
                    </Form.Item>
                    <Form.Item name="retention_days" label="retention_days（可选）">
                      <InputNumber min={1} style={{ width: '100%' }} />
                    </Form.Item>
                  </Space>
                ),
              },
              {
                key: 'bind',
                label: '执行绑定',
                children: (
                  <Space direction="vertical" style={{ width: '100%' }} size="middle">
                    <Radio.Group
                      value={bindingMode}
                      onChange={(e) => {
                        setBindingMode(e.target.value);
                        if (e.target.value === 'none') {
                          form.setFieldsValue({ bound_agent_id: undefined, bound_agent_pool_id: undefined });
                        }
                      }}
                    >
                      <Radio.Button value="none">不绑定</Radio.Button>
                      <Radio.Button value="agent">指定 Agent</Radio.Button>
                      <Radio.Button value="pool">指定池</Radio.Button>
                    </Radio.Group>
                    {bindingMode === 'agent' ? (
                      <Form.Item name="bound_agent_id" label="Agent" rules={[{ required: true }]}>
                        <Select
                          showSearch
                          optionFilterProp="label"
                          options={tenantAgents.map((a) => ({
                            value: a.id,
                            label: `${a.hostname ?? a.id} (${a.id})`,
                          }))}
                        />
                      </Form.Item>
                    ) : null}
                    {bindingMode === 'pool' ? (
                      <Form.Item name="bound_agent_pool_id" label="Agent 池" rules={[{ required: true }]}>
                        <Select
                          showSearch
                          optionFilterProp="label"
                          options={pools.map((p) => ({
                            value: p.id,
                            label: `${p.name} (${p.id})`,
                          }))}
                        />
                      </Form.Item>
                    ) : null}
                    <Space>
                      <Link to="/execution/tenant-agents">租户内 Agents</Link>
                      <span>|</span>
                      <Link to="/execution/agent-pools">Agent 池</Link>
                    </Space>
                  </Space>
                ),
              },
            ]}
          />
          {access.canWrite ? (
            <Button type="primary" onClick={() => void onSave()} style={{ marginTop: 16 }}>
              保存
            </Button>
          ) : null}
        </Form>
      </Card>

      {!isNew && policyId ? (
        <Card title="关联备份计划（本策略）" style={{ marginTop: 16 }}>
          {access.canWrite ? (
            <Button type="primary" onClick={() => setSchOpen(true)} style={{ marginBottom: 12 }}>
              新建计划
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
        title="新建备份计划"
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
          message.success('已创建计划');
          schForm.resetFields();
          setSchOpen(false);
          await loadAux();
          scheduleRef.current?.reload();
        }}
        destroyOnClose
      >
        <Form form={schForm} layout="vertical">
          <Form.Item name="cron_expression" label="Cron（五段）" rules={[{ required: true }]}>
            <Input placeholder="0 2 * * *" />
          </Form.Item>
          <Form.Item name="timezone" label="时区" initialValue="UTC">
            <Input />
          </Form.Item>
          <Form.Item name="enabled" label="启用" valuePropName="checked" initialValue>
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </PageContainer>
  );
};

export default PolicyEditPage;
