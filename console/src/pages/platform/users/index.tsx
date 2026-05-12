import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { request, useIntl } from '@umijs/max';
import { Alert, App, Button, Form, Modal, Popconfirm, Select, Space } from 'antd';
import React, { useEffect, useMemo, useRef, useState } from 'react';

import { IAM_API_PREFIX, isIamConsoleEnabled } from '@/config/iam';
import { STORAGE_TENANT_ID_KEY } from '@/constants/storage';
import { detailFromError } from '@/requestErrorConfig';

type MemberRow = {
  id: string;
  user_id: string;
  email: string;
  role: string;
  status: string;
};

const PlatformUsersPage: React.FC = () => {
  const { formatMessage } = useIntl();
  const { message } = App.useApp();
  const actionRef = useRef<ActionType>();
  const [tenantOptions, setTenantOptions] = useState<{ label: string; value: string }[]>([]);
  const [tenantId, setTenantId] = useState<string | null>(() =>
    typeof window !== 'undefined' ? localStorage.getItem(STORAGE_TENANT_ID_KEY) : null,
  );
  const [editRow, setEditRow] = useState<MemberRow | null>(null);
  const [form] = Form.useForm<{ role: string }>();

  useEffect(() => {
    if (editRow) form.setFieldsValue({ role: editRow.role });
  }, [editRow, form]);

  useEffect(() => {
    void (async () => {
      try {
        const rows = await request<API.TenantOut[]>('/api/v1/tenants', { method: 'GET' });
        setTenantOptions(rows.map((r) => ({ label: `${r.name} (${r.slug})`, value: r.id })));
      } catch {
        setTenantOptions([]);
      }
    })();
  }, []);

  const columns: ProColumns<MemberRow>[] = useMemo(
    () => [
      { title: formatMessage({ id: 'page.platformUsers.list.colEmail' }), dataIndex: 'email', copyable: true },
      { title: formatMessage({ id: 'page.platformUsers.list.colRole' }), dataIndex: 'role', width: 140 },
      { title: formatMessage({ id: 'page.platformUsers.list.colStatus' }), dataIndex: 'status', width: 120 },
      {
        title: formatMessage({ id: 'page.platformUsers.list.colActions' }),
        valueType: 'option',
        width: 160,
        render: (_, r) => (
          <Space size="small">
            <Button type="link" size="small" onClick={() => setEditRow(r)}>
              {formatMessage({ id: 'page.platformUsers.list.editRole' })}
            </Button>
            <Popconfirm
              title={formatMessage({ id: 'page.platformUsers.list.removeConfirm' })}
              onConfirm={async () => {
                if (!tenantId) return;
                try {
                  await request(`${IAM_API_PREFIX}/v1/tenants/${tenantId}/members/${r.id}`, {
                    method: 'DELETE',
                    skipErrorHandler: true,
                  });
                  message.success(formatMessage({ id: 'page.platformUsers.list.removed' }));
                  actionRef.current?.reload();
                } catch (e) {
                  message.error(detailFromError(e));
                }
              }}
            >
              <Button type="link" size="small" danger>
                {formatMessage({ id: 'page.platformUsers.list.remove' })}
              </Button>
            </Popconfirm>
          </Space>
        ),
      },
    ],
    [formatMessage, message, tenantId],
  );

  if (!isIamConsoleEnabled()) {
    return (
      <PageContainer title={formatMessage({ id: 'page.platformUsers.list.title' })}>
        <Alert type="warning" showIcon message={formatMessage({ id: 'page.platformUsers.list.iamOnly' })} />
      </PageContainer>
    );
  }

  return (
    <PageContainer title={formatMessage({ id: 'page.platformUsers.list.title' })}>
      <div style={{ marginBottom: 16, maxWidth: 520 }}>
        <span style={{ marginRight: 8 }}>{formatMessage({ id: 'page.platformUsers.list.tenant' })}</span>
        <Select
          style={{ minWidth: 280 }}
          allowClear
          showSearch
          optionFilterProp="label"
          options={tenantOptions}
          placeholder={formatMessage({ id: 'page.platformUsers.list.tenantPh' })}
          value={tenantId ?? undefined}
          onChange={(v) => {
            const next = v || null;
            setTenantId(next);
            if (typeof window !== 'undefined') {
              if (next) localStorage.setItem(STORAGE_TENANT_ID_KEY, next);
              else localStorage.removeItem(STORAGE_TENANT_ID_KEY);
            }
            actionRef.current?.reload();
          }}
        />
      </div>
      {!tenantId ? (
        <p>{formatMessage({ id: 'page.platformUsers.list.pickTenant' })}</p>
      ) : (
        <ProTable<MemberRow>
          rowKey="id"
          actionRef={actionRef}
          search={false}
          columns={columns}
          pagination={{ pageSize: 20 }}
          request={async () => {
            const data = await request<MemberRow[]>(`${IAM_API_PREFIX}/v1/tenants/${tenantId}/members`, {
              method: 'GET',
              skipErrorHandler: true,
            });
            return { data, success: true, total: data.length };
          }}
        />
      )}

      <Modal
        title={formatMessage({ id: 'page.platformUsers.list.editTitle' })}
        open={Boolean(editRow)}
        destroyOnClose
        onCancel={() => {
          setEditRow(null);
          form.resetFields();
        }}
        onOk={async () => {
          if (!tenantId || !editRow) return;
          const v = await form.validateFields();
          try {
            await request(`${IAM_API_PREFIX}/v1/tenants/${tenantId}/members/${editRow.id}`, {
              method: 'PATCH',
              data: { role: v.role },
              skipErrorHandler: true,
            });
            message.success(formatMessage({ id: 'page.platformUsers.list.updated' }));
            setEditRow(null);
            form.resetFields();
            actionRef.current?.reload();
          } catch (e) {
            message.error(detailFromError(e));
          }
        }}
      >
        <Form key={editRow?.id ?? 'none'} form={form} layout="vertical">
          <Form.Item name="role" label={formatMessage({ id: 'page.platformUsers.create.role' })} rules={[{ required: true }]}>
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
    </PageContainer>
  );
};

export default PlatformUsersPage;
