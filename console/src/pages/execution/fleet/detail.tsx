import { PageContainer } from '@ant-design/pro-components';
import { history, request, useAccess, useParams } from '@umijs/max';
import { App, Button, Card, Form, Input, Modal, Select, Typography } from 'antd';
import React, { useCallback, useEffect, useState } from 'react';

const FleetAgentDetailPage: React.FC = () => {
  const { agentId } = useParams<{ agentId: string }>();
  const { message } = App.useApp();
  const access = useAccess();
  const [agent, setAgent] = useState<API.EdgeAgentOut | null>(null);
  const [enrollment, setEnrollment] = useState<API.AgentEnrollmentOut | null>(null);
  const [enr404, setEnr404] = useState(false);
  const [loading, setLoading] = useState(true);
  const [tenants, setTenants] = useState<API.TenantRow[]>([]);
  const [form] = Form.useForm();
  const [revokeOpen, setRevokeOpen] = useState(false);
  const [revokeForm] = Form.useForm();

  const load = useCallback(async () => {
    if (!agentId) return;
    setLoading(true);
    try {
      const a = await request<API.EdgeAgentOut>(`/api/v1/agents/${agentId}`);
      setAgent(a);
      try {
        const e = await request<API.AgentEnrollmentOut>(`/api/v1/agents/${agentId}/enrollment`, {
          skipErrorHandler: true,
        });
        setEnrollment(e);
        setEnr404(false);
        form.setFieldsValue({ allowed_tenant_ids: e.allowed_tenant_ids });
      } catch {
        setEnrollment(null);
        setEnr404(true);
        form.setFieldsValue({ allowed_tenant_ids: [] });
      }
    } finally {
      setLoading(false);
    }
  }, [agentId, form]);

  useEffect(() => {
    void load();
    void request<API.TenantRow[]>('/api/v1/tenants').then(setTenants);
  }, [load]);

  if (!agentId) return null;

  return (
    <PageContainer title={`Agent ${agentId}`} loading={loading} onBack={() => history.push('/execution/fleet')}>
      {agent ? (
        <Card title="快照">
          <pre style={{ fontSize: 12, background: '#f5f5f5', padding: 12, borderRadius: 8, overflow: 'auto' }}>
            {JSON.stringify(agent, null, 2)}
          </pre>
        </Card>
      ) : null}

      <Card title="租户登记（Enrollment）" style={{ marginTop: 16 }}>
        {enr404 ? (
          <Typography.Paragraph type="warning">
            尚无登记记录（404）。管理员可通过下方表单创建（PUT 即 upsert）。
          </Typography.Paragraph>
        ) : null}
        {access.canAdmin ? (
          <Form
            form={form}
            layout="vertical"
            onFinish={async (v) => {
              const ids = v.allowed_tenant_ids as string[];
              if (!ids?.length) {
                message.error('至少选择一个租户 UUID（API 要求非空列表）');
                return;
              }
              await request(`/api/v1/agents/${agentId}/enrollment`, {
                method: 'PUT',
                data: { allowed_tenant_ids: ids },
              });
              message.success('已保存登记');
              void load();
            }}
          >
            <Form.Item
              name="allowed_tenant_ids"
              label="allowed_tenant_ids"
              rules={[{ required: true, message: '至少一项' }]}
            >
              <Select
                mode="multiple"
                showSearch
                optionFilterProp="label"
                options={tenants.map((t) => ({
                  value: t.id,
                  label: `${t.name} (${t.slug}) · ${t.id}`,
                }))}
              />
            </Form.Item>
            <Form.Item>
              <Button type="primary" htmlType="submit">
                保存登记（PUT）
              </Button>
            </Form.Item>
          </Form>
        ) : enrollment ? (
          <pre style={{ fontSize: 12 }}>{JSON.stringify(enrollment, null, 2)}</pre>
        ) : (
          <Typography.Text type="secondary">无登记数据或不可读。</Typography.Text>
        )}
      </Card>

      {access.canAdmin ? (
        <Card title="吊销 gRPC 会话" style={{ marginTop: 16 }}>
          <Typography.Paragraph type="secondary">
            调用 <Typography.Text code>POST /api/v1/agents/…/revoke-grpc-sessions</Typography.Text>
            ，使 Register 签发的 Bearer 全部失效。须强确认。
          </Typography.Paragraph>
          <Button danger onClick={() => setRevokeOpen(true)}>
            吊销 gRPC 会话
          </Button>
          <Modal
            title="确认吊销 gRPC 会话"
            open={revokeOpen}
            onCancel={() => {
              setRevokeOpen(false);
              revokeForm.resetFields();
            }}
            okText="执行吊销"
            okButtonProps={{ danger: true }}
            onOk={async () => {
              const v = await revokeForm.validateFields();
              if (String(v.confirm).trim() !== 'REVOKE') {
                message.error('确认框须输入大写 REVOKE');
                throw new Error('abort');
              }
              const res = await request<{ session_generation: number }>(
                `/api/v1/agents/${agentId}/revoke-grpc-sessions`,
                { method: 'POST' },
              );
              message.success(`已吊销，session_generation=${res.session_generation}`);
              setRevokeOpen(false);
              revokeForm.resetFields();
            }}
            destroyOnClose
          >
            <Form form={revokeForm} layout="vertical">
              <Form.Item
                name="confirm"
                label='请输入大写 "REVOKE" 以确认'
                rules={[{ required: true }]}
              >
                <Input autoComplete="off" placeholder="REVOKE" />
              </Form.Item>
            </Form>
          </Modal>
        </Card>
      ) : null}
    </PageContainer>
  );
};

export default FleetAgentDetailPage;
