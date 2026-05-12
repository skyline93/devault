import { PageContainer } from '@ant-design/pro-components';
import { request, useAccess, useIntl } from '@umijs/max';
import { App, Button, Card, Descriptions, Form, Input, Radio, Select, Space, Steps } from 'antd';
import React, { useEffect, useMemo, useState } from 'react';

const BackupRunPage: React.FC = () => {
  const { formatMessage } = useIntl();
  const { message } = App.useApp();
  const access = useAccess();
  const [form] = Form.useForm();
  const [policies, setPolicies] = useState<API.PolicyOut[]>([]);
  const [step, setStep] = useState(0);
  const mode = (Form.useWatch('mode', form) as 'policy' | 'inline' | undefined) ?? 'policy';

  useEffect(() => {
    void request<API.PolicyOut[]>('/api/v1/policies').then(setPolicies);
  }, []);

  const stepItems = useMemo(
    () => [
      {
        title: formatMessage({ id: 'page.backupRun.stepChoose' }),
        description: formatMessage({ id: 'page.backupRun.stepChooseDesc' }),
      },
      {
        title: formatMessage({ id: 'page.backupRun.stepParams' }),
        description:
          mode === 'policy'
            ? formatMessage({ id: 'page.backupRun.stepParamsPolicy' })
            : formatMessage({ id: 'page.backupRun.stepParamsInline' }),
      },
      {
        title: formatMessage({ id: 'page.backupRun.stepConfirm' }),
        description: formatMessage({ id: 'page.backupRun.stepConfirmDesc' }),
      },
    ],
    [formatMessage, mode],
  );

  if (!access.canWrite) {
    return (
      <PageContainer title={formatMessage({ id: 'page.backupRun.title' })}>
        <Card>{formatMessage({ id: 'page.backupRun.noWrite' })}</Card>
      </PageContainer>
    );
  }

  const summary = () => {
    const v = form.getFieldsValue(true);
    if (mode === 'policy') {
      const p = policies.find((x) => x.id === v.policy_id);
      return {
        mode: formatMessage({ id: 'page.backupRun.modeSummaryPolicy' }),
        policy: p ? `${p.name} (${p.id})` : v.policy_id,
      };
    }
    return {
      mode: formatMessage({ id: 'page.backupRun.modeSummaryInline' }),
      preview: (v.configJson as string)?.slice(0, 200) ?? '',
    };
  };

  const submit = async () => {
    const namePaths =
      mode === 'policy'
        ? (['mode', 'policy_id', 'idempotency_key'] as const)
        : (['mode', 'configJson', 'inline_plugin', 'idempotency_key'] as const);
      const v = await form.validateFields([...namePaths, 'inline_plugin']);
    if (mode === 'policy') {
      if (!v.policy_id) {
        message.error(formatMessage({ id: 'page.backupRun.missingPolicy' }));
        return;
      }
      await request('/api/v1/jobs/backup', {
        method: 'POST',
        data: {
          policy_id: v.policy_id,
          idempotency_key: v.idempotency_key || undefined,
        },
      });
    } else {
      if (v.configJson == null || String(v.configJson).trim() === '') {
        message.error(formatMessage({ id: 'page.backupRun.missingInline' }));
        return;
      }
      let config: Record<string, unknown>;
      try {
        config = JSON.parse(v.configJson as string) as Record<string, unknown>;
      } catch {
        message.error(formatMessage({ id: 'page.backupRun.jsonInvalid' }));
        return;
      }
      if (!config.version) config.version = 1;
      const pl = (v.inline_plugin as 'file' | 'postgres_pgbackrest') || 'file';
      await request('/api/v1/jobs/backup', {
        method: 'POST',
        data: {
          plugin: pl,
          config,
          idempotency_key: v.idempotency_key || undefined,
        },
      });
    }
    message.success(formatMessage({ id: 'page.backupRun.queued' }));
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
      /* validation shown by form */
    }
  };

  const s = summary();
  const dash = formatMessage({ id: 'page.backupRun.dash' });

  return (
    <PageContainer title={formatMessage({ id: 'page.backupRun.title' })}>
      <Card>
        <Steps current={step} style={{ marginBottom: 24 }} items={stepItems} />

        <Form form={form} layout="vertical" initialValues={{ mode: 'policy', inline_plugin: 'file' }}>
          {step === 0 ? (
            <>
              <Form.Item name="mode" label={formatMessage({ id: 'page.backupRun.modeLabel' })}>
                <Radio.Group
                  options={[
                    { label: formatMessage({ id: 'page.backupRun.modePolicy' }), value: 'policy' },
                    { label: formatMessage({ id: 'page.backupRun.modeInline' }), value: 'inline' },
                  ]}
                />
              </Form.Item>
              <Button type="primary" onClick={() => setStep(1)}>
                {formatMessage({ id: 'page.backupRun.next' })}
              </Button>
            </>
          ) : null}

          {step === 1 ? (
            <>
              {mode === 'policy' ? (
                <Form.Item
                  name="policy_id"
                  label={formatMessage({ id: 'page.backupRun.policyLabel' })}
                  rules={[{ required: true, message: formatMessage({ id: 'page.backupRun.policyRequired' }) }]}
                >
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
                <>
                  <Form.Item name="inline_plugin" label={formatMessage({ id: 'page.backupRun.inlinePluginLabel' })}>
                    <Radio.Group
                      options={[
                        { label: formatMessage({ id: 'page.backupRun.inlinePluginFile' }), value: 'file' },
                        {
                          label: formatMessage({ id: 'page.backupRun.inlinePluginPg' }),
                          value: 'postgres_pgbackrest',
                        },
                      ]}
                    />
                  </Form.Item>
                  <Form.Item
                    name="configJson"
                    label={formatMessage({ id: 'page.backupRun.configJsonLabel' })}
                    rules={[{ required: true, message: formatMessage({ id: 'page.backupRun.jsonRequired' }) }]}
                  >
                    <Input.TextArea
                      rows={14}
                      placeholder={`{\n  "version": 1,\n  "paths": ["/data"],\n  "excludes": []\n}`}
                    />
                  </Form.Item>
                </>
              )}
              <Form.Item name="idempotency_key" label={formatMessage({ id: 'page.backupRun.idempotencyLabel' })}>
                <Input />
              </Form.Item>
              <Space>
                <Button onClick={() => setStep(0)}>{formatMessage({ id: 'page.backupRun.prev' })}</Button>
                <Button type="primary" onClick={() => void nextFrom1()}>
                  {formatMessage({ id: 'page.backupRun.next' })}
                </Button>
              </Space>
            </>
          ) : null}

          {step === 2 ? (
            <>
              <Descriptions bordered column={1} size="small" style={{ marginBottom: 16 }}>
                <Descriptions.Item label={formatMessage({ id: 'page.backupRun.summaryMode' })}>{s.mode}</Descriptions.Item>
                {mode === 'policy' ? (
                  <Descriptions.Item label={formatMessage({ id: 'page.backupRun.summaryPolicy' })}>
                    {String((s as { policy?: string }).policy ?? dash)}
                  </Descriptions.Item>
                ) : (
                  <Descriptions.Item label={formatMessage({ id: 'page.backupRun.summaryJson' })}>
                    <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: 12 }}>
                      {String((s as { preview?: string }).preview)}
                    </pre>
                  </Descriptions.Item>
                )}
                <Descriptions.Item label={formatMessage({ id: 'page.backupRun.summaryIdem' })}>
                  {(form.getFieldsValue(true).idempotency_key as string) || dash}
                </Descriptions.Item>
              </Descriptions>
              <Space>
                <Button onClick={() => setStep(1)}>{formatMessage({ id: 'page.backupRun.prev' })}</Button>
                <Button type="primary" onClick={() => void submit()}>
                  {formatMessage({ id: 'page.backupRun.confirmSubmit' })}
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
