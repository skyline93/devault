import { PageContainer, ProTable } from '@ant-design/pro-components';
import { history, Link, request, useAccess, useParams } from '@umijs/max';
import { App, Button, Card, Form, InputNumber, Modal, Select, Space, Typography } from 'antd';
import React, { useCallback, useEffect, useState } from 'react';

const PoolDetailPage: React.FC = () => {
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
      title={detail?.name ?? '池详情'}
      loading={loading}
      onBack={() => history.push('/execution/agent-pools')}
    >
      <Typography.Paragraph type="secondary">
        成员整表替换（<Typography.Text code>PUT /api/v1/agent-pools/…/members</Typography.Text>
        ）。策略侧绑定见
        <Link to="/backup/policies"> 策略 </Link>（池 ID：<Typography.Text code>{poolId}</Typography.Text>）。
      </Typography.Paragraph>
      <Card title="成员">
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
                      <InputNumber min={1} max={1000000} placeholder="weight" />
                    </Form.Item>
                    <Form.Item {...rest} name={[name, 'sort_order']}>
                      <InputNumber placeholder="sort_order" />
                    </Form.Item>
                    <Button type="link" danger onClick={() => remove(name)}>
                      移除
                    </Button>
                  </Space>
                ))}
                <Button type="dashed" onClick={() => add({ weight: 100, sort_order: 0 })} block>
                  添加成员
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
                message.success('已保存成员');
                void load();
              }}
            >
              保存成员
            </Button>
          ) : null}
        </Form>
      </Card>

      <Card title="当前成员快照" style={{ marginTop: 16 }}>
        <ProTable<API.AgentPoolMemberOut>
          rowKey="agent_id"
          search={false}
          pagination={false}
          columns={[
            {
              title: 'Agent',
              dataIndex: 'agent_id',
              render: (_, r) => <Link to={`/execution/fleet/${r.agent_id}`}>{r.agent_id}</Link>,
            },
            { title: 'weight', dataIndex: 'weight', width: 100 },
            { title: 'sort_order', dataIndex: 'sort_order', width: 100 },
            { title: 'last_seen_at', dataIndex: 'last_seen_at', valueType: 'dateTime', width: 170 },
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
                title: '删除整个池？',
                content: '将清除引用本池的策略绑定。',
                onOk: async () => {
                  await request(`/api/v1/agent-pools/${poolId}`, { method: 'DELETE' });
                  message.success('已删除');
                  history.push('/execution/agent-pools');
                },
              });
            }}
          >
            删除池
          </Button>
        ) : null}
      </Card>
    </PageContainer>
  );
};

export default PoolDetailPage;
