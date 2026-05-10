import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { history, Link, request, useAccess } from '@umijs/max';
import { App, Button, Form, Input, Modal } from 'antd';
import React, { useRef, useState } from 'react';

const AgentPoolsPage: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
  const actionRef = useRef<ActionType>();
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm();

  const columns: ProColumns<API.AgentPoolOut>[] = [
    {
      title: '名称',
      dataIndex: 'name',
      render: (_, r) => <Link to={`/execution/agent-pools/${r.id}`}>{r.name}</Link>,
    },
    { title: '创建时间', dataIndex: 'created_at', valueType: 'dateTime', width: 170 },
    {
      title: '操作',
      valueType: 'option',
      width: 120,
      render: (_, row) => (
        <Link to={`/execution/agent-pools/${row.id}`}>成员与详情</Link>
      ),
    },
  ];

  return (
    <PageContainer
      title="Agent 池"
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
            新建池
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
        title="新建 Agent 池"
        open={open}
        onCancel={() => setOpen(false)}
        onOk={async () => {
          const v = await form.validateFields();
          const created = await request<API.AgentPoolOut>('/api/v1/agent-pools', {
            method: 'POST',
            data: { name: v.name },
          });
          message.success('已创建');
          setOpen(false);
          actionRef.current?.reload();
          history.push(`/execution/agent-pools/${created.id}`);
        }}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input maxLength={255} />
          </Form.Item>
        </Form>
      </Modal>
    </PageContainer>
  );
};

export default AgentPoolsPage;
