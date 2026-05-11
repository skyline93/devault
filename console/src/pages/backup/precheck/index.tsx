import { PageContainer } from '@ant-design/pro-components';
import { request, useAccess, useIntl } from '@umijs/max';
import { App, Button, Card, Form, Select } from 'antd';
import React, { useEffect, useState } from 'react';

const PrecheckPage: React.FC = () => {
  const { formatMessage } = useIntl();
  const { message } = App.useApp();
  const access = useAccess();
  const [form] = Form.useForm();
  const [policies, setPolicies] = useState<API.PolicyOut[]>([]);

  useEffect(() => {
    void request<API.PolicyOut[]>('/api/v1/policies').then(setPolicies);
  }, []);

  if (!access.canWrite) {
    return (
      <PageContainer title={formatMessage({ id: 'page.backupPrecheck.title' })}>
        <Card>{formatMessage({ id: 'page.backupPrecheck.noWrite' })}</Card>
      </PageContainer>
    );
  }

  return (
    <PageContainer title={formatMessage({ id: 'page.backupPrecheck.title' })}>
      <Card>
        <p style={{ marginBottom: 16, color: 'rgba(0,0,0,0.45)' }}>{formatMessage({ id: 'page.backupPrecheck.intro' })}</p>
        <Form
          form={form}
          layout="vertical"
          onFinish={async (v) => {
            const res = await request<{ job_id: string; status: string }>('/api/v1/jobs/path-precheck', {
              method: 'POST',
              data: { policy_id: v.policy_id },
            });
            message.success(formatMessage({ id: 'page.backupPrecheck.queued' }, { jobId: res.job_id }));
            form.resetFields();
          }}
        >
          <Form.Item name="policy_id" label={formatMessage({ id: 'page.backupPrecheck.policy' })} rules={[{ required: true }]}>
            <Select
              showSearch
              optionFilterProp="label"
              options={policies.map((p) => ({
                value: p.id,
                label: `${p.name} (${p.id})`,
              }))}
            />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">
              {formatMessage({ id: 'page.backupPrecheck.submit' })}
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </PageContainer>
  );
};

export default PrecheckPage;
