import { PageContainer } from '@ant-design/pro-components';
import { request, useAccess } from '@umijs/max';
import { App, Button, Card, Descriptions, Form, Input, Radio, Select, Space, Steps } from 'antd';
import React, { useEffect, useState } from 'react';

const BackupRunPage: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
  const [form] = Form.useForm();
  const [policies, setPolicies] = useState<API.PolicyOut[]>([]);
  const [step, setStep] = useState(0);
  const mode = (Form.useWatch('mode', form) as 'policy' | 'inline' | undefined) ?? 'policy';

  useEffect(() => {
    void request<API.PolicyOut[]>('/api/v1/policies').then(setPolicies);
  }, []);

  if (!access.canWrite) {
    return (
      <PageContainer title="发起备份">
        <Card>当前角色无写权限。</Card>
      </PageContainer>
    );
  }

  const summary = () => {
    // Steps 会卸载中间步骤的 Form.Item；用 true 取回含已卸载字段在内的整表 store（与 rc-field-form 行为一致）。
    const v = form.getFieldsValue(true);
    if (mode === 'policy') {
      const p = policies.find((x) => x.id === v.policy_id);
      return { mode: '按策略', policy: p ? `${p.name} (${p.id})` : v.policy_id };
    }
    return { mode: '内联 JSON', preview: (v.configJson as string)?.slice(0, 200) ?? '' };
  };

  const submit = async () => {
    // 第三步无 policy_id/configJson 的 Form.Item 挂载；无参 validateFields 返回 {}，会导致未带 policy_id/config。
    const namePaths =
      mode === 'policy' ? (['mode', 'policy_id', 'idempotency_key'] as const) : (['mode', 'configJson', 'idempotency_key'] as const);
    const v = await form.validateFields([...namePaths]);
    if (mode === 'policy') {
      if (!v.policy_id) {
        message.error('缺少策略，请返回上一步选择策略');
        return;
      }
      await request('/api/v1/jobs/backup', {
        method: 'POST',
        data: {
          plugin: 'file',
          policy_id: v.policy_id,
          idempotency_key: v.idempotency_key || undefined,
        },
      });
    } else {
      if (v.configJson == null || String(v.configJson).trim() === '') {
        message.error('缺少内联配置，请返回上一步填写 JSON');
        return;
      }
      let config: Record<string, unknown>;
      try {
        config = JSON.parse(v.configJson as string) as Record<string, unknown>;
      } catch {
        message.error('内联 config 须为合法 JSON');
        return;
      }
      if (!config.version) config.version = 1;
      await request('/api/v1/jobs/backup', {
        method: 'POST',
        data: {
          plugin: 'file',
          config,
          idempotency_key: v.idempotency_key || undefined,
        },
      });
    }
    message.success('已入队备份作业');
    form.resetFields();
    setStep(0);
  };

  const nextFrom1 = async () => {
    try {
      if (mode === 'policy') {
        await form.validateFields(['policy_id']);
      } else {
        await form.validateFields(['configJson']);
      }
      setStep(2);
    } catch {
      /* Form 已提示 */
    }
  };

  const s = summary();

  return (
    <PageContainer title="发起备份">
      <Card>
        <Steps
          current={step}
          style={{ marginBottom: 24 }}
          items={[
            { title: '选择方式', description: '策略或内联配置' },
            { title: '填写参数', description: mode === 'policy' ? 'policy_id 等' : 'JSON' },
            { title: '确认并入队', description: '核对后提交' },
          ]}
        />

        <Form form={form} layout="vertical" initialValues={{ mode: 'policy' }}>
          {step === 0 ? (
            <>
              <Form.Item name="mode" label="方式">
                <Radio.Group
                  options={[
                    { label: '按策略 policy_id', value: 'policy' },
                    { label: '内联 FileBackupConfigV1（JSON）', value: 'inline' },
                  ]}
                />
              </Form.Item>
              <Button type="primary" onClick={() => setStep(1)}>
                下一步
              </Button>
            </>
          ) : null}

          {step === 1 ? (
            <>
              {mode === 'policy' ? (
                <Form.Item name="policy_id" label="策略" rules={[{ required: true, message: '请选择策略' }]}>
                  <Select
                    showSearch
                    optionFilterProp="label"
                    options={policies.map((p) => ({
                      value: p.id,
                      label: `${p.name} (${p.id})`,
                    }))}
                  />
                </Form.Item>
              ) : (
                <Form.Item
                  name="configJson"
                  label="config JSON"
                  rules={[{ required: true, message: '请输入 JSON' }]}
                >
                  <Input.TextArea
                    rows={14}
                    placeholder={`{\n  "version": 1,\n  "paths": ["/data"],\n  "excludes": []\n}`}
                  />
                </Form.Item>
              )}
              <Form.Item name="idempotency_key" label="幂等键（可选）">
                <Input />
              </Form.Item>
              <Space>
                <Button onClick={() => setStep(0)}>上一步</Button>
                <Button type="primary" onClick={() => void nextFrom1()}>
                  下一步
                </Button>
              </Space>
            </>
          ) : null}

          {step === 2 ? (
            <>
              <Descriptions bordered column={1} size="small" style={{ marginBottom: 16 }}>
                <Descriptions.Item label="方式">{s.mode}</Descriptions.Item>
                {mode === 'policy' ? (
                  <Descriptions.Item label="策略">{String(s.policy ?? '—')}</Descriptions.Item>
                ) : (
                  <Descriptions.Item label="JSON 摘要">
                    <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: 12 }}>{String(s.preview)}</pre>
                  </Descriptions.Item>
                )}
                <Descriptions.Item label="幂等键">
                  {(form.getFieldsValue(true).idempotency_key as string) || '—'}
                </Descriptions.Item>
              </Descriptions>
              <Space>
                <Button onClick={() => setStep(1)}>上一步</Button>
                <Button type="primary" onClick={() => void submit()}>
                  确认并入队
                </Button>
              </Space>
            </>
          ) : null}
        </Form>
      </Card>
    </PageContainer>
  );
};

export default BackupRunPage;
