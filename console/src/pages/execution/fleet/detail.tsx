import { PageContainer } from '@ant-design/pro-components';
import { history, request, useAccess, useIntl, useParams } from '@umijs/max';
import { App, Button, Card, Form, Input, Modal, Select, Typography } from 'antd';
import React, { useCallback, useEffect, useState } from 'react';

const FleetAgentDetailPage: React.FC = () => {
  const { formatMessage } = useIntl();
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
    <PageContainer
      title={formatMessage({ id: 'page.fleetDetail.pageTitle' }, { agentId })}
      loading={loading}
      onBack={() => history.push('/execution/fleet')}
    >
      {agent ? (
        <Card title={formatMessage({ id: 'page.fleetDetail.snapshot' })}>
          <pre style={{ fontSize: 12, background: '#f5f5f5', padding: 12, borderRadius: 8, overflow: 'auto' }}>
            {JSON.stringify(agent, null, 2)}
          </pre>
        </Card>
      ) : null}

      <Card title={formatMessage({ id: 'page.fleetDetail.enrollment' })} style={{ marginTop: 16 }}>
        {enr404 ? (
          <Typography.Paragraph type="warning">{formatMessage({ id: 'page.fleetDetail.enrollmentEmpty' })}</Typography.Paragraph>
        ) : null}
        {access.canAdmin ? (
          <Form
            form={form}
            layout="vertical"
            onFinish={async (v) => {
              const ids = v.allowed_tenant_ids as string[];
              if (!ids?.length) {
                message.error(formatMessage({ id: 'page.fleetDetail.enrollmentErr' }));
                return;
              }
              await request(`/api/v1/agents/${agentId}/enrollment`, {
                method: 'PUT',
                data: { allowed_tenant_ids: ids },
              });
              message.success(formatMessage({ id: 'page.fleetDetail.enrollmentSaved' }));
              void load();
            }}
          >
            <Form.Item
              name="allowed_tenant_ids"
              label={formatMessage({ id: 'page.fleetDetail.organizationsLabel' })}
              rules={[{ required: true, message: formatMessage({ id: 'page.fleetDetail.membersRequired' }) }]}
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
                {formatMessage({ id: 'page.fleetDetail.saveEnrollment' })}
              </Button>
            </Form.Item>
          </Form>
        ) : enrollment ? (
          <pre style={{ fontSize: 12 }}>{JSON.stringify(enrollment, null, 2)}</pre>
        ) : (
          <Typography.Text type="secondary">{formatMessage({ id: 'page.fleetDetail.noEnrollment' })}</Typography.Text>
        )}
      </Card>

      {access.canAdmin ? (
        <Card title={formatMessage({ id: 'page.fleetDetail.revokeCard' })} style={{ marginTop: 16 }}>
          <Typography.Paragraph type="secondary">{formatMessage({ id: 'page.fleetDetail.revokeIntro' })}</Typography.Paragraph>
          <Button danger onClick={() => setRevokeOpen(true)}>
            {formatMessage({ id: 'page.fleetDetail.revokeBtn' })}
          </Button>
          <Modal
            title={formatMessage({ id: 'page.fleetDetail.revokeModalTitle' })}
            open={revokeOpen}
            onCancel={() => {
              setRevokeOpen(false);
              revokeForm.resetFields();
            }}
            okText={formatMessage({ id: 'page.fleetDetail.revokeOk' })}
            okButtonProps={{ danger: true }}
            onOk={async () => {
              const v = await revokeForm.validateFields();
              if (String(v.confirm).trim() !== 'REVOKE') {
                message.error(formatMessage({ id: 'page.fleetDetail.revokeTypeErr' }));
                throw new Error('abort');
              }
              const res = await request<{ session_generation: number }>(
                `/api/v1/agents/${agentId}/revoke-grpc-sessions`,
                { method: 'POST' },
              );
              message.success(formatMessage({ id: 'page.fleetDetail.revokeDone' }, { generation: res.session_generation }));
              setRevokeOpen(false);
              revokeForm.resetFields();
            }}
            destroyOnClose
          >
            <Form form={revokeForm} layout="vertical">
              <Form.Item name="confirm" label={formatMessage({ id: 'page.fleetDetail.revokeConfirmLabel' })} rules={[{ required: true }]}>
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
