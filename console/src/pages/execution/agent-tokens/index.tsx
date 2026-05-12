import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { request, useAccess, useIntl } from '@umijs/max';
import { App, Button, Form, Input, Modal, Space, Tag } from 'antd';
import React, { useMemo, useRef, useState } from 'react';

const AgentTokensPage: React.FC = () => {
  const { formatMessage } = useIntl();
  const { message } = App.useApp();
  const access = useAccess();
  const actionRef = useRef<ActionType>();
  const [createOpen, setCreateOpen] = useState(false);
  const [createForm] = Form.useForm();

  const columns: ProColumns<API.AgentTokenOut>[] = useMemo(
    () => [
      {
        title: formatMessage({ id: 'page.agentTokens.colLabel' }),
        dataIndex: 'label',
        ellipsis: true,
      },
      {
        title: formatMessage({ id: 'page.agentTokens.colDescription' }),
        dataIndex: 'description',
        ellipsis: true,
        render: (_, r) => r.description ?? '—',
      },
      {
        title: formatMessage({ id: 'page.agentTokens.colInstances' }),
        dataIndex: 'instance_count',
        width: 96,
      },
      {
        title: formatMessage({ id: 'page.agentTokens.colStatus' }),
        dataIndex: 'disabled_at',
        width: 100,
        render: (_, r) =>
          r.disabled_at ? (
            <Tag>{formatMessage({ id: 'page.agentTokens.statusDisabled' })}</Tag>
          ) : (
            <Tag color="green">{formatMessage({ id: 'page.agentTokens.statusActive' })}</Tag>
          ),
      },
      {
        title: formatMessage({ id: 'page.agentTokens.colCreated' }),
        dataIndex: 'created_at',
        valueType: 'dateTime',
        width: 170,
      },
      {
        title: formatMessage({ id: 'page.agentTokens.colActions' }),
        valueType: 'option',
        width: 120,
        render: (_, row) =>
          access.canWrite ? (
            <Button
              type="link"
              size="small"
              danger
              disabled={Boolean(row.disabled_at)}
              onClick={() => {
                Modal.confirm({
                  title: formatMessage({ id: 'page.agentTokens.disableTitle' }),
                  content: formatMessage({ id: 'page.agentTokens.disableContent' }),
                  okType: 'danger',
                  onOk: async () => {
                    await request(`/api/v1/agent-tokens/${row.id}/disable`, { method: 'POST' });
                    message.success(formatMessage({ id: 'page.agentTokens.disabledOk' }));
                    actionRef.current?.reload();
                  },
                });
              }}
            >
              {formatMessage({ id: 'page.agentTokens.disable' })}
            </Button>
          ) : null,
      },
    ],
    [access.canWrite, formatMessage, message],
  );

  return (
    <PageContainer
      title={formatMessage({ id: 'page.agentTokens.title' })}
      extra={
        access.canWrite ? (
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
            {formatMessage({ id: 'page.agentTokens.create' })}
          </Button>
        ) : undefined
      }
    >
      <ProTable<API.AgentTokenOut>
        rowKey="id"
        actionRef={actionRef}
        columns={columns}
        search={false}
        request={async () => {
          const data = await request<API.AgentTokenOut[]>('/api/v1/agent-tokens');
          return { data, success: true, total: data.length };
        }}
        pagination={{ pageSize: 20 }}
      />

      <Modal
        title={formatMessage({ id: 'page.agentTokens.modalCreateTitle' })}
        open={createOpen}
        onCancel={() => {
          setCreateOpen(false);
          createForm.resetFields();
        }}
        okText={formatMessage({ id: 'page.agentTokens.createSubmit' })}
        onOk={async () => {
          const v = await createForm.validateFields();
          const created = await request<API.AgentTokenCreatedOut>('/api/v1/agent-tokens', {
            method: 'POST',
            data: {
              label: v.label,
              description: v.description?.trim() ? v.description.trim() : null,
            },
          });
          message.success(formatMessage({ id: 'page.agentTokens.createdOk' }));
          setCreateOpen(false);
          createForm.resetFields();
          actionRef.current?.reload();
          Modal.info({
            title: formatMessage({ id: 'page.agentTokens.secretTitle' }),
            width: 560,
            content: (
              <Space direction="vertical" style={{ width: '100%' }}>
                <span>{formatMessage({ id: 'page.agentTokens.secretWarning' })}</span>
                <Input.TextArea value={created.plaintext_secret} autoSize={{ minRows: 3 }} readOnly />
              </Space>
            ),
          });
        }}
        destroyOnClose
      >
        <Form form={createForm} layout="vertical">
          <Form.Item
            name="label"
            label={formatMessage({ id: 'page.agentTokens.fieldLabel' })}
            rules={[{ required: true, message: formatMessage({ id: 'page.agentTokens.labelRequired' }) }]}
          >
            <Input maxLength={255} />
          </Form.Item>
          <Form.Item name="description" label={formatMessage({ id: 'page.agentTokens.fieldDescription' })}>
            <Input.TextArea rows={3} maxLength={2048} showCount />
          </Form.Item>
        </Form>
      </Modal>
    </PageContainer>
  );
};

export default AgentTokensPage;
