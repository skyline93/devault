import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { request, useIntl } from '@umijs/max';
import { App, Button, Form, Input, Modal, Select } from 'antd';
import React, { useMemo, useRef, useState } from 'react';

import { STORAGE_TENANT_ID_KEY } from '@/constants/storage';

type InvitationRow = {
  id: string;
  tenant_id: string;
  email: string;
  role: 'tenant_admin' | 'operator' | 'auditor';
  created_at: string;
  expires_at: string;
  accepted_at: string | null;
};

const TeamInvitationsPage: React.FC = () => {
  const { formatMessage } = useIntl();
  const { message } = App.useApp();
  const actionRef = useRef<ActionType>();
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm();

  const tenantId = typeof window !== 'undefined' ? localStorage.getItem(STORAGE_TENANT_ID_KEY) : null;

  const columns: ProColumns<InvitationRow>[] = useMemo(
    () => [
      { title: formatMessage({ id: 'page.teamInvites.colEmail' }), dataIndex: 'email' },
      { title: formatMessage({ id: 'page.teamInvites.colRole' }), dataIndex: 'role', width: 120 },
      { title: formatMessage({ id: 'page.teamInvites.colCreated' }), dataIndex: 'created_at', width: 200 },
      { title: formatMessage({ id: 'page.teamInvites.colExpires' }), dataIndex: 'expires_at', width: 200 },
    ],
    [formatMessage],
  );

  return (
    <PageContainer title={formatMessage({ id: 'page.teamInvites.title' })}>
      {!tenantId ? (
        <p>{formatMessage({ id: 'page.teamInvites.selectTenant' })}</p>
      ) : (
        <>
          <div style={{ marginBottom: 16 }}>
            <Button type="primary" onClick={() => setOpen(true)}>
              {formatMessage({ id: 'page.teamInvites.send' })}
            </Button>
          </div>
          <ProTable<InvitationRow>
            rowKey="id"
            actionRef={actionRef}
            columns={columns}
            search={false}
            request={async () => {
              const data = await request<InvitationRow[]>(`/api/v1/tenants/${tenantId}/invitations`, {
                method: 'GET',
              });
              return { data, success: true, total: data.length };
            }}
            pagination={{ pageSize: 20 }}
          />
          <Modal
            title={formatMessage({ id: 'page.teamInvites.modalTitle' })}
            open={open}
            onCancel={() => setOpen(false)}
            okText={formatMessage({ id: 'page.teamInvites.okSend' })}
            destroyOnClose
            onOk={async () => {
              const v = await form.validateFields();
              await request(`/api/v1/tenants/${tenantId}/invitations`, {
                method: 'POST',
                data: { email: v.email, role: v.role },
              });
              message.success(formatMessage({ id: 'page.teamInvites.sent' }));
              setOpen(false);
              form.resetFields();
              actionRef.current?.reload();
            }}
          >
            <Form form={form} layout="vertical">
              <Form.Item name="email" label={formatMessage({ id: 'page.teamInvites.email' })} rules={[{ required: true, type: 'email' }]}>
                <Input />
              </Form.Item>
              <Form.Item name="role" label={formatMessage({ id: 'page.teamInvites.role' })} initialValue="operator" rules={[{ required: true }]}>
                <Select
                  options={[
                    { value: 'tenant_admin', label: 'tenant_admin' },
                    { value: 'operator', label: 'operator' },
                    { value: 'auditor', label: 'auditor' },
                  ]}
                />
              </Form.Item>
            </Form>
          </Modal>
        </>
      )}
    </PageContainer>
  );
};

export default TeamInvitationsPage;
