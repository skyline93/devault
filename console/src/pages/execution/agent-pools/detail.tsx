import { PageContainer, ProTable } from '@ant-design/pro-components';
import { history, Link, request, useAccess, useIntl, useParams } from '@umijs/max';
import { App, Button, Card, Form, InputNumber, Modal, Select, Space, Typography } from 'antd';
import React, { useCallback, useEffect, useState } from 'react';

const PoolDetailPage: React.FC = () => {
  const { formatMessage } = useIntl();
  const { poolId } = useParams<{ poolId: string }>();
  const { message } = App.useApp();
  const access = useAccess();
  const [detail, setDetail] = useState<API.AgentPoolDetailOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [tenantAgents, setTenantAgents] = useState<API.TenantScopedAgentOut[]>([]);
  const [form] = Form.useForm();

  const load = useCallback(async () => {
    if (!poolId) return;
    setLoading(true);
    try {
      const d = await request<API.AgentPoolDetailOut>(`/api/v1/agent-pools/${poolId}`);
      setDetail(d);
      form.setFieldsValue({
        members: d.members.map((m) => ({
          agent_id: m.agent_id,
          weight: m.weight,
          sort_order: m.sort_order,
        })),
      });
    } finally {
      setLoading(false);
    }
  }, [poolId, form]);

  useEffect(() => {
    void load();
    void request<API.TenantScopedAgentOut[]>('/api/v1/tenant-agents').then(setTenantAgents);
  }, [load]);

  if (!poolId) return null;

  const agentOptions = tenantAgents.map((a) => ({
    value: a.id,
    label: `${a.hostname ?? a.id} (${a.id})`,
  }));

  return (
    <PageContainer
      title={detail?.name ?? formatMessage({ id: 'menu.execution.agent-pool-detail' })}
      loading={loading}
      onBack={() => history.push('/execution/agent-pools')}
    >
      <Typography.Paragraph type="secondary">
        {formatMessage({ id: 'page.agentPoolDetail.intro' })}{' '}
        <Link to="/backup/policies">{formatMessage({ id: 'page.agentPoolDetail.policiesLink' })}</Link>
        {' · '}
        <Typography.Text code>{poolId}</Typography.Text>
      </Typography.Paragraph>
      <Card title={formatMessage({ id: 'page.agentPoolDetail.members' })}>
        <Form form={form} disabled={!access.canWrite}>
          <Form.List name="members">
            {(fields, { add, remove }) => (
              <>
                {fields.map(({ key, name, ...rest }) => (
                  <Space key={key} align="baseline" style={{ display: 'flex', marginBottom: 8 }}>
                    <Form.Item {...rest} name={[name, 'agent_id']} rules={[{ required: true }]}>
                      <Select showSearch optionFilterProp="label" options={agentOptions} style={{ minWidth: 280 }} />
                    </Form.Item>
                    <Form.Item {...rest} name={[name, 'weight']} rules={[{ required: true }]}>
                      <InputNumber min={1} max={1000000} placeholder={formatMessage({ id: 'page.agentPoolDetail.weightPh' })} />
                    </Form.Item>
                    <Form.Item {...rest} name={[name, 'sort_order']}>
                      <InputNumber placeholder={formatMessage({ id: 'page.agentPoolDetail.orderPh' })} />
                    </Form.Item>
                    <Button type="link" danger onClick={() => remove(name)}>
                      {formatMessage({ id: 'page.agentPoolDetail.remove' })}
                    </Button>
                  </Space>
                ))}
                <Button type="dashed" onClick={() => add({ weight: 100, sort_order: 0 })} block>
                  {formatMessage({ id: 'page.agentPoolDetail.addMember' })}
                </Button>
              </>
            )}
          </Form.List>
          {access.canWrite ? (
            <Button
              type="primary"
              style={{ marginTop: 16 }}
              onClick={async () => {
                const v = await form.validateFields();
                const members = (v.members ?? []).map(
                  (m: { agent_id: string; weight: number; sort_order?: number }) => ({
                    agent_id: m.agent_id,
                    weight: m.weight ?? 100,
                    sort_order: m.sort_order ?? 0,
                  }),
                );
                await request(`/api/v1/agent-pools/${poolId}/members`, {
                  method: 'PUT',
                  data: { members },
                });
                message.success(formatMessage({ id: 'page.agentPoolDetail.saved' }));
                void load();
              }}
            >
              {formatMessage({ id: 'page.agentPoolDetail.saveMembers' })}
            </Button>
          ) : null}
        </Form>
      </Card>

      <Card title={formatMessage({ id: 'page.agentPoolDetail.snapshotTitle' })} style={{ marginTop: 16 }}>
        <ProTable<API.AgentPoolMemberOut>
          rowKey="agent_id"
          search={false}
          pagination={false}
          columns={[
            {
              title: formatMessage({ id: 'page.agentPoolDetail.colAgent' }),
              dataIndex: 'agent_id',
              render: (_, r) => <Link to={`/execution/fleet/${r.agent_id}`}>{r.agent_id}</Link>,
            },
            { title: formatMessage({ id: 'page.agentPoolDetail.colWeight' }), dataIndex: 'weight', width: 100 },
            { title: formatMessage({ id: 'page.agentPoolDetail.colSort' }), dataIndex: 'sort_order', width: 100 },
            {
              title: formatMessage({ id: 'page.agentPoolDetail.colLastSeen' }),
              dataIndex: 'last_seen_at',
              valueType: 'dateTime',
              width: 170,
            },
          ]}
          dataSource={detail?.members ?? []}
          toolBarRender={false}
        />
        {access.canWrite ? (
          <Button
            danger
            style={{ marginTop: 12 }}
            onClick={() => {
              Modal.confirm({
                title: formatMessage({ id: 'page.agentPoolDetail.deletePoolTitle' }),
                content: formatMessage({ id: 'page.agentPoolDetail.deletePoolContent' }),
                onOk: async () => {
                  await request(`/api/v1/agent-pools/${poolId}`, { method: 'DELETE' });
                  message.success(formatMessage({ id: 'page.agentPoolDetail.poolDeleted' }));
                  history.push('/execution/agent-pools');
                },
              });
            }}
          >
            {formatMessage({ id: 'page.agentPoolDetail.deletePool' })}
          </Button>
        ) : null}
      </Card>
    </PageContainer>
  );
};

export default PoolDetailPage;
