import { PageContainer } from '@ant-design/pro-components';
import { request, useAccess } from '@umijs/max';
import { App, Button, Card, Form, Select } from 'antd';
import React, { useEffect, useState } from 'react';

const PrecheckPage: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
  const [form] = Form.useForm();
  const [policies, setPolicies] = useState<API.PolicyOut[]>([]);

  useEffect(() => {
    void request<API.PolicyOut[]>('/api/v1/policies').then(setPolicies);
  }, []);

  if (!access.canWrite) {
    return (
      <PageContainer title="路径预检">
        <Card>当前角色无写权限。</Card>
      </PageContainer>
    );
  }

  return (
    <PageContainer title="路径预检">
      <Card>
        <p style={{ marginBottom: 16, color: 'rgba(0,0,0,0.45)' }}>
          对所选策略的 <code>paths</code> 在已租约 Agent 上执行只读存在性检查（<code>POST /api/v1/jobs/path-precheck</code>）。
        </p>
        <Form
          form={form}
          layout="vertical"
          onFinish={async (v) => {
            const res = await request<{ job_id: string; status: string }>('/api/v1/jobs/path-precheck', {
              method: 'POST',
              data: { policy_id: v.policy_id },
            });
            message.success(`已入队预检作业 ${res.job_id}`);
            form.resetFields();
          }}
        >
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
          <Form.Item>
            <Button type="primary" htmlType="submit">
              提交预检
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </PageContainer>
  );
};

export default PrecheckPage;
