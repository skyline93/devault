import { LockOutlined, UserOutlined } from '@ant-design/icons';
import { LoginForm, ProFormText } from '@ant-design/pro-components';
import { history, Link, request, useIntl, useModel } from '@umijs/max';
import { Alert, Card, theme, Typography } from 'antd';
import React, { useState } from 'react';

import { STORAGE_BEARER_KEY } from '@/constants/storage';
import { IAM_API_PREFIX, isIamConsoleEnabled } from '@/config/iam';

type IamTokenOut = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  tenant_id: string;
  permissions: string[];
};

const SelfRegister: React.FC = () => {
  const { formatMessage } = useIntl();
  const { token } = theme.useToken();
  const { setInitialState } = useModel('@@initialState');
  const [ok, setOk] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: token.colorBgLayout,
        padding: 24,
      }}
    >
      <Card style={{ width: 'min(440px, 100%)' }} bordered={false}>
        <Typography.Title level={4} style={{ textAlign: 'center' }}>
          {formatMessage({ id: 'page.register.title' })}
        </Typography.Title>
        <Typography.Paragraph type="secondary" style={{ textAlign: 'center' }}>
          {isIamConsoleEnabled()
            ? formatMessage({ id: 'page.register.subtitleIam' })
            : formatMessage({ id: 'page.register.subtitleLegacy' })}{' '}
          {formatMessage({ id: 'page.register.backPrefix' })}{' '}
          <Link to="/user/login">{formatMessage({ id: 'page.register.passwordLogin' })}</Link>
        </Typography.Paragraph>
        {ok ? <Alert type="success" message={ok} style={{ marginBottom: 16 }} /> : null}
        {err ? <Alert type="error" message={err} style={{ marginBottom: 16 }} /> : null}
        <LoginForm
          submitter={{ searchConfig: { submitText: formatMessage({ id: 'page.register.submit' }) } }}
          onFinish={async (values) => {
            setErr(null);
            setOk(null);
            const email = (values as { email?: string }).email?.trim();
            const password = (values as { password?: string }).password;
            if (!email || !password) {
              setErr(formatMessage({ id: 'page.register.emailPasswordRequired' }));
              return;
            }
            try {
              if (isIamConsoleEnabled()) {
                const tok = await request<IamTokenOut>(`${IAM_API_PREFIX}/v1/auth/register`, {
                  method: 'POST',
                  data: {
                    email,
                    password,
                    name: email.split('@')[0] || 'user',
                  },
                  skipErrorHandler: true,
                });
                localStorage.setItem(STORAGE_BEARER_KEY, tok.access_token);
                const currentUser = await request<API.CurrentUser>('/api/v1/auth/session', {
                  method: 'GET',
                  skipErrorHandler: true,
                });
                const gated = Boolean(currentUser.needs_mfa);
                await setInitialState((s) => ({
                  ...s,
                  currentUser,
                  canAdmin: Boolean(!gated && currentUser.role === 'admin'),
                  canWrite: Boolean(!gated && (currentUser.role === 'admin' || currentUser.role === 'operator')),
                  canInviteMembers: Boolean(
                    !gated && currentUser.tenants?.some((t) => t.membership_role === 'tenant_admin'),
                  ),
                }));
                history.push('/overview/welcome');
                return;
              }
              await request('/api/v1/auth/register', {
                method: 'POST',
                data: {
                  email,
                  password,
                },
                skipErrorHandler: true,
              });
              setOk(formatMessage({ id: 'page.register.createdPending' }));
            } catch (e) {
              const st = (e as { response?: { status?: number; data?: { detail?: string } } })?.response?.status;
              const d = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
              if (st === 403) setErr(typeof d === 'string' ? d : formatMessage({ id: 'page.register.closed' }));
              else if (st === 409) setErr(formatMessage({ id: 'page.register.conflict' }));
              else setErr(typeof d === 'string' ? d : formatMessage({ id: 'page.register.failed' }));
            }
          }}
        >
          <ProFormText
            name="email"
            fieldProps={{ prefix: <UserOutlined /> }}
            placeholder={formatMessage({ id: 'page.register.emailPh' })}
            rules={[{ required: true }]}
          />
          <ProFormText.Password
            name="password"
            fieldProps={{ prefix: <LockOutlined /> }}
            placeholder={formatMessage({ id: 'page.register.passwordPh' })}
            rules={[{ required: true, min: 12 }]}
          />
        </LoginForm>
      </Card>
    </div>
  );
};

export default SelfRegister;
