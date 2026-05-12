import { PageContainer, ProForm, ProFormSelect, ProFormText, type ProFormInstance } from '@ant-design/pro-components';
import { history, request, useIntl } from '@umijs/max';
import { App, Alert, Button, Modal, Space, Typography } from 'antd';
import React, { useRef, useState } from 'react';

import { IAM_API_PREFIX, isIamConsoleEnabled } from '@/config/iam';
import { detailFromError } from '@/requestErrorConfig';
import { generateInitialPassword } from '@/utils/generate-initial-password';

type IamPlatformUserOut = {
  id: string;
  email: string;
  name: string;
  status: string;
  is_platform_admin: boolean;
  must_change_password: boolean;
};

const PlatformUserCreatePage: React.FC = () => {
  const { formatMessage } = useIntl();
  const { message } = App.useApp();
  const formRef = useRef<ProFormInstance>(null);
  const [doneOpen, setDoneOpen] = useState(false);
  const [initialPwd, setInitialPwd] = useState('');
  const [createdEmail, setCreatedEmail] = useState('');

  if (!isIamConsoleEnabled()) {
    return (
      <PageContainer title={formatMessage({ id: 'page.platformUsers.create.title' })}>
        <Alert type="warning" showIcon message={formatMessage({ id: 'page.platformUsers.create.iamOnly' })} />
      </PageContainer>
    );
  }

  return (
    <PageContainer title={formatMessage({ id: 'page.platformUsers.create.title' })}>
      <ProForm<{ tenant_id: string; email: string; name?: string; role: string }>
        formRef={formRef}
        layout="vertical"
        style={{ maxWidth: 520 }}
        onFinish={async (values) => {
          const pwd = generateInitialPassword();
          try {
            await request<IamPlatformUserOut>(`${IAM_API_PREFIX}/v1/platform/users`, {
              method: 'POST',
              data: {
                email: values.email.trim(),
                password: pwd,
                name: (values.name || '').trim() || undefined,
                must_change_password: true,
              },
              skipErrorHandler: true,
            });
            try {
              await request(`${IAM_API_PREFIX}/v1/tenants/${values.tenant_id}/members`, {
                method: 'POST',
                data: { email: values.email.trim().toLowerCase(), role: values.role },
                skipErrorHandler: true,
              });
            } catch (e) {
              Modal.error({
                title: formatMessage({ id: 'page.platformUsers.create.memberFailedTitle' }),
                content: (
                  <div>
                    <p>{detailFromError(e)}</p>
                    <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
                      {formatMessage({ id: 'page.platformUsers.create.memberFailedHint' })}
                    </Typography.Paragraph>
                  </div>
                ),
              });
              return;
            }
            setInitialPwd(pwd);
            setCreatedEmail(values.email.trim());
            setDoneOpen(true);
            message.success(formatMessage({ id: 'page.platformUsers.create.success' }));
            formRef.current?.resetFields();
          } catch (e) {
            message.error(detailFromError(e));
          }
        }}
        submitter={{
          searchConfig: { submitText: formatMessage({ id: 'page.platformUsers.create.submit' }) },
        }}
      >
        <ProFormSelect
          name="tenant_id"
          label={formatMessage({ id: 'page.platformUsers.create.tenant' })}
          rules={[{ required: true, message: formatMessage({ id: 'page.platformUsers.create.tenantRequired' }) }]}
          request={async () => {
            const rows = await request<API.TenantOut[]>('/api/v1/tenants', { method: 'GET' });
            return rows.map((r) => ({ label: `${r.name} (${r.slug})`, value: r.id }));
          }}
          showSearch
          fieldProps={{ optionFilterProp: 'label' }}
        />
        <ProFormText
          name="email"
          label={formatMessage({ id: 'page.platformUsers.create.email' })}
          rules={[
            { required: true, message: formatMessage({ id: 'page.platformUsers.create.emailRequired' }) },
            { type: 'email', message: formatMessage({ id: 'page.platformUsers.create.emailInvalid' }) },
          ]}
        />
        <ProFormText name="name" label={formatMessage({ id: 'page.platformUsers.create.displayName' })} />
        <ProFormSelect
          name="role"
          label={formatMessage({ id: 'page.platformUsers.create.role' })}
          initialValue="operator"
          rules={[{ required: true }]}
          options={[
            { value: 'tenant_admin', label: 'tenant_admin' },
            { value: 'operator', label: 'operator' },
            { value: 'auditor', label: 'auditor' },
          ]}
        />
        <Alert type="info" showIcon message={formatMessage({ id: 'page.platformUsers.create.passwordHint' })} />
      </ProForm>

      <Modal
        title={formatMessage({ id: 'page.platformUsers.create.doneTitle' })}
        open={doneOpen}
        footer={
          <Space>
            <Button
              type="primary"
              onClick={() => {
                setDoneOpen(false);
                history.push('/platform/users');
              }}
            >
              {formatMessage({ id: 'page.platformUsers.create.goManage' })}
            </Button>
            <Button
              onClick={() => {
                setDoneOpen(false);
                history.push('/platform/users/new');
              }}
            >
              {formatMessage({ id: 'page.platformUsers.create.createAnother' })}
            </Button>
          </Space>
        }
        onCancel={() => setDoneOpen(false)}
        destroyOnClose
      >
        <Typography.Paragraph>
          <strong>{formatMessage({ id: 'page.platformUsers.create.doneEmail' })}</strong> {createdEmail}
        </Typography.Paragraph>
        <Typography.Paragraph type="secondary">{formatMessage({ id: 'page.platformUsers.create.doneWarn' })}</Typography.Paragraph>
        <Typography.Paragraph copyable code style={{ fontSize: 14, wordBreak: 'break-all' }}>
          {initialPwd}
        </Typography.Paragraph>
      </Modal>
    </PageContainer>
  );
};

export default PlatformUserCreatePage;
