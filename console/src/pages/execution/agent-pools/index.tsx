import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { history, Link, request, useAccess, useIntl } from '@umijs/max';
import { App, Button, Form, Input, Modal } from 'antd';
import React, { useMemo, useRef, useState } from 'react';

const AgentPoolsPage: React.FC = () => {
  const { formatMessage } = useIntl();
  const { message } = App.useApp();
  const access = useAccess();
  const actionRef = useRef<ActionType>();
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm();

  const columns: ProColumns<API.AgentPoolOut>[] = useMemo(
    () => [
      {
        title: formatMessage({ id: 'page.agentPools.colName' }),
        dataIndex: 'name',
        render: (_, r) => <Link to={`/execution/agent-pools/${r.id}`}>{r.name}</Link>,
      },
      { title: formatMessage({ id: 'page.agentPools.colCreated' }), dataIndex: 'created_at', valueType: 'dateTime', width: 170 },
      {
        title: formatMessage({ id: 'page.agentPools.colActions' }),
        valueType: 'option',
        width: 160,
        render: (_, row) => <Link to={`/execution/agent-pools/${row.id}`}>{formatMessage({ id: 'page.agentPools.detailLink' })}</Link>,
      },
    ],
    [formatMessage],
  );

  return (
    <PageContainer
      title={formatMessage({ id: 'page.agentPools.title' })}
      extra={
        access.canWrite ? (
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              form.resetFields();
              setOpen(true);
            }}
          >
            {formatMessage({ id: 'page.agentPools.new' })}
          </Button>
        ) : undefined
      }
    >
      <ProTable<API.AgentPoolOut>
        rowKey="id"
        actionRef={actionRef}
        columns={columns}
        search={false}
        request={async () => {
          const data = await request<API.AgentPoolOut[]>('/api/v1/agent-pools');
          return { data, success: true, total: data.length };
        }}
        pagination={{ pageSize: 20 }}
      />

      <Modal
        title={formatMessage({ id: 'page.agentPools.modalTitle' })}
        open={open}
        onCancel={() => setOpen(false)}
        onOk={async () => {
          const v = await form.validateFields();
          const created = await request<API.AgentPoolOut>('/api/v1/agent-pools', {
            method: 'POST',
            data: { name: v.name },
          });
          message.success(formatMessage({ id: 'page.agentPools.created' }));
          setOpen(false);
          actionRef.current?.reload();
          history.push(`/execution/agent-pools/${created.id}`);
        }}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label={formatMessage({ id: 'page.agentPools.name' })} rules={[{ required: true }]}>
            <Input maxLength={255} />
          </Form.Item>
        </Form>
      </Modal>
    </PageContainer>
  );
};

export default AgentPoolsPage;
