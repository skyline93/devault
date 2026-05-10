import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { request } from '@umijs/max';
import { App, Button, Form, Input, Modal, Select } from 'antd';
import React, { useRef, useState } from 'react';

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

/** §十六-11：租户管理员向邮箱发送加入租户的邀请。 */
const TeamInvitationsPage: React.FC = () => {
  const { message } = App.useApp();
  const actionRef = useRef<ActionType>();
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm();

  const tenantId = typeof window !== 'undefined' ? localStorage.getItem(STORAGE_TENANT_ID_KEY) : null;

  const columns: ProColumns<InvitationRow>[] = [
    { title: '邮箱', dataIndex: 'email' },
    { title: '角色', dataIndex: 'role', width: 120 },
    { title: '创建时间', dataIndex: 'created_at', width: 200 },
    { title: '过期时间', dataIndex: 'expires_at', width: 200 },
  ];

  return (
    <PageContainer title="成员邀请">
      {!tenantId ? (
        <p>请先在顶栏选择租户。</p>
      ) : (
        <>
          <div style={{ marginBottom: 16 }}>
            <Button type="primary" onClick={() => setOpen(true)}>
              发送邀请
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
            title="邀请加入当前租户"
            open={open}
            onCancel={() => setOpen(false)}
            okText="发送"
            destroyOnClose
            onOk={async () => {
              const v = await form.validateFields();
              await request(`/api/v1/tenants/${tenantId}/invitations`, {
                method: 'POST',
                data: { email: v.email, role: v.role },
              });
              message.success('邀请已发送（邮件可能因 SMTP 未配置仅记日志）');
              setOpen(false);
              form.resetFields();
              actionRef.current?.reload();
            }}
          >
            <Form form={form} layout="vertical">
              <Form.Item name="email" label="邮箱" rules={[{ required: true, type: 'email' }]}>
                <Input />
              </Form.Item>
              <Form.Item name="role" label="成员角色" initialValue="operator" rules={[{ required: true }]}>
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
