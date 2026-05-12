import { PageContainer } from '@ant-design/pro-components';
import { history, request, useAccess, useIntl } from '@umijs/max';
import { App, Button, Card, Col, Form, Input, Row, Switch } from 'antd';
import React, { useCallback, useEffect, useState } from 'react';
import PolicyFormFields from './PolicyFormFields';
import { bindingPayloadFromValues, buildConfigPayloadFromValues, parseConfig } from './policyPayload';

const PolicyNewPage: React.FC = () => {
  const { formatMessage } = useIntl();
  const { message } = App.useApp();
  const access = useAccess();
  const [form] = Form.useForm();
  const [tenantAgents, setTenantAgents] = useState<API.TenantScopedAgentOut[]>([]);

  const loadAgents = useCallback(async () => {
    const ta = await request<API.TenantScopedAgentOut[]>('/api/v1/tenant-agents');
    setTenantAgents(ta);
  }, []);

  useEffect(() => {
    void loadAgents();
  }, [loadAgents]);

  useEffect(() => {
    form.setFieldsValue({
      name: '',
      ...parseConfig({ version: 1, paths: [] }),
      encrypt_artifacts: true,
      initial_schedule_timezone: 'UTC',
      initial_schedule_enabled: true,
    });
  }, [form]);

  const onSave = async () => {
    try {
      const values = await form.validateFields();
      const config = buildConfigPayloadFromValues(values);
      const bind = bindingPayloadFromValues(values);

      const created = await request<API.PolicyOut>('/api/v1/policies', {
        method: 'POST',
        data: {
          name: values.name,
          plugin: 'file',
          enabled: true,
          config,
          ...bind,
        },
      });

      const cron = String(values.initial_schedule_cron ?? '').trim();
      if (cron) {
        try {
          await request('/api/v1/schedules', {
            method: 'POST',
            data: {
              policy_id: created.id,
              cron_expression: cron,
              timezone: String(values.initial_schedule_timezone || 'UTC').trim() || 'UTC',
              enabled: values.initial_schedule_enabled !== false,
            },
          });
        } catch {
          message.error(formatMessage({ id: 'page.policyEdit.scheduleCreatePartialFail' }));
          history.push('/backup/policies');
          return;
        }
      }

      message.success(formatMessage({ id: 'page.policyEdit.policyCreated' }));
      history.push('/backup/policies');
    } catch (e: unknown) {
      const err = e as { errorFields?: unknown };
      if (err?.errorFields) return;
      message.error(formatMessage({ id: 'page.policyEdit.policyCreateFailed' }));
    }
  };

  return (
    <PageContainer title={formatMessage({ id: 'page.policyEdit.newTitle' })} onBack={() => history.push('/backup/policies')}>
      <Card>
        <Form form={form} layout="vertical" disabled={!access.canWrite}>
          <PolicyFormFields tenantAgents={tenantAgents} pathsAgentDisabled={false} />

          <Card
            size="small"
            title={formatMessage({ id: 'page.policyEdit.optionalScheduleSection' })}
            style={{ marginTop: 16 }}
          >
            <div style={{ marginBottom: 12, color: 'var(--ant-color-text-secondary)', fontSize: 12 }}>
              {formatMessage({ id: 'page.policyEdit.optionalScheduleIntro' })}
            </div>
            <Row gutter={[16, 8]}>
              <Col xs={24} md={12}>
                <Form.Item name="initial_schedule_cron" label={formatMessage({ id: 'page.policyEdit.cron' })}>
                  <Input placeholder="0 2 * * *" />
                </Form.Item>
              </Col>
              <Col xs={24} md={12}>
                <Form.Item name="initial_schedule_timezone" label={formatMessage({ id: 'page.policyEdit.timezone' })}>
                  <Input />
                </Form.Item>
              </Col>
            </Row>
            <Form.Item
              name="initial_schedule_enabled"
              label={formatMessage({ id: 'page.policyEdit.scheduleEnabled' })}
              valuePropName="checked"
            >
              <Switch />
            </Form.Item>
          </Card>

          {access.canWrite ? (
            <Button type="primary" onClick={() => void onSave()} style={{ marginTop: 16 }}>
              {formatMessage({ id: 'page.policyEdit.save' })}
            </Button>
          ) : null}
        </Form>
      </Card>
    </PageContainer>
  );
};

export default PolicyNewPage;
