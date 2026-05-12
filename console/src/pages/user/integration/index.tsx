import { LockOutlined } from '@ant-design/icons';
import { LoginForm, ProFormText } from '@ant-design/pro-components';
import { history, Link, request, useIntl, useModel } from '@umijs/max';
import { Alert, Card, theme, Typography } from 'antd';
import React, { useState } from 'react';

import { STORAGE_BEARER_KEY, STORAGE_REFRESH_TOKEN_KEY } from '@/constants/storage';
import { computeSessionAccessFlags } from '@/utils/auth-access';

const ApiIntegrationLogin: React.FC = () => {
  const { formatMessage } = useIntl();
  const { token } = theme.useToken();
  const { setInitialState } = useModel('@@initialState');
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
        <div style={{ marginBottom: 16, textAlign: 'center' }}>
          <h1 style={{ margin: 0, fontSize: 22 }}>{formatMessage({ id: 'page.integration.title' })}</h1>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            {formatMessage({ id: 'page.integration.subtitle' })}
          </Typography.Paragraph>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            <Link to="/user/login">{formatMessage({ id: 'page.integration.passwordLoginLink' })}</Link>
          </Typography.Paragraph>
        </div>
        {err ? <Alert type="error" showIcon message={err} style={{ marginBottom: 16 }} closable onClose={() => setErr(null)} /> : null}
        <LoginForm
          submitter={{ searchConfig: { submitText: formatMessage({ id: 'page.integration.submit' }) } }}
          onFinish={async (values) => {
            const raw = (values as { token?: string }).token?.trim() ?? '';
            setErr(null);
            if (raw) {
              localStorage.setItem(STORAGE_BEARER_KEY, raw);
            } else {
              localStorage.removeItem(STORAGE_BEARER_KEY);
              localStorage.removeItem(STORAGE_REFRESH_TOKEN_KEY);
            }
            try {
              const currentUser = await request<API.CurrentUser>('/api/v1/auth/session', {
                method: 'GET',
                skipErrorHandler: true,
              });
              const flags = computeSessionAccessFlags(currentUser);
              await setInitialState((s) => ({
                ...s,
                currentUser,
                canAdmin: flags.canAdmin,
                canWrite: flags.canWrite,
                canInviteMembers: flags.canInviteMembers,
                needsPasswordChange: flags.needsPasswordChange,
              }));
              history.push('/overview/welcome');
            } catch (e) {
              localStorage.removeItem(STORAGE_BEARER_KEY);
              localStorage.removeItem(STORAGE_REFRESH_TOKEN_KEY);
              const status = (e as { response?: { status?: number } })?.response?.status;
              setErr(
                status === 401 || status === 403
                  ? formatMessage({ id: 'page.integration.tokenInvalid' })
                  : formatMessage({ id: 'page.integration.network' }),
              );
            }
          }}
        >
          <ProFormText.Password
            name="token"
            fieldProps={{ size: 'large', prefix: <LockOutlined /> }}
            placeholder={formatMessage({ id: 'page.integration.tokenPlaceholder' })}
          />
        </LoginForm>
      </Card>
    </div>
  );
};

export default ApiIntegrationLogin;
