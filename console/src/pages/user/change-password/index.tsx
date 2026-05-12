import { LockOutlined } from '@ant-design/icons';
import { LoginForm, ProFormText } from '@ant-design/pro-components';
import { history, Link, request, useIntl, useModel } from '@umijs/max';
import { Alert, App, Card, theme, Typography } from 'antd';
import React, { useEffect, useState } from 'react';

import { IAM_API_PREFIX, isIamConsoleEnabled } from '@/config/iam';
import { LOGIN_PATH } from '@/constants/auth-routes';
import { STORAGE_BEARER_KEY, STORAGE_REFRESH_TOKEN_KEY } from '@/constants/storage';
import { authDebug } from '@/utils/auth-debug';
import { computeSessionAccessFlags, setPasswordChangePending } from '@/utils/auth-access';
import { waitNextPaint } from '@/utils/wait-next-paint';

type IamTokenOut = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  tenant_id?: string | null;
  permissions: string[];
  must_change_password?: boolean;
};

const ChangePasswordPage: React.FC = () => {
  const { formatMessage } = useIntl();
  const { token } = theme.useToken();
  const { message } = App.useApp();
  const { setInitialState } = useModel('@@initialState');
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!isIamConsoleEnabled()) return;
    const bearer = typeof window !== 'undefined' ? localStorage.getItem(STORAGE_BEARER_KEY) : null;
    if (!bearer) {
      history.replace(LOGIN_PATH);
    }
  }, []);

  if (!isIamConsoleEnabled()) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
        <Card style={{ width: 'min(440px, 100%)' }}>
          <Alert type="warning" showIcon message={formatMessage({ id: 'page.changePassword.iamOnly' })} />
          <Typography.Paragraph style={{ marginTop: 16, marginBottom: 0 }}>
            <Link to={LOGIN_PATH}>{formatMessage({ id: 'page.changePassword.backLogin' })}</Link>
          </Typography.Paragraph>
        </Card>
      </div>
    );
  }

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
        <div style={{ marginBottom: 24, textAlign: 'center' }}>
          <h1 style={{ margin: 0, fontSize: 22 }}>{formatMessage({ id: 'page.changePassword.title' })}</h1>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0, marginTop: 8 }}>
            {formatMessage({ id: 'page.changePassword.subtitle' })}
          </Typography.Paragraph>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0, marginTop: 8 }}>
            <Link to={LOGIN_PATH}>{formatMessage({ id: 'page.changePassword.backLogin' })}</Link>
          </Typography.Paragraph>
        </div>
        {err ? (
          <Alert type="error" showIcon message={err} style={{ marginBottom: 16 }} closable onClose={() => setErr(null)} />
        ) : null}
        <LoginForm
          submitter={{ searchConfig: { submitText: formatMessage({ id: 'page.changePassword.submit' }) } }}
          onFinish={async (values) => {
            const current_password = (values as { current_password?: string }).current_password ?? '';
            const new_password = (values as { new_password?: string }).new_password ?? '';
            const new_password2 = (values as { new_password2?: string }).new_password2 ?? '';
            if (new_password !== new_password2) {
              setErr(formatMessage({ id: 'page.changePassword.mismatch' }));
              return;
            }
            setErr(null);
            try {
              await request(`${IAM_API_PREFIX}/v1/auth/change-password`, {
                method: 'POST',
                data: { current_password, new_password },
                skipErrorHandler: true,
              });
              setPasswordChangePending(false);
              const rawRefresh = localStorage.getItem(STORAGE_REFRESH_TOKEN_KEY);
              if (rawRefresh) {
                try {
                  const tok = await request<IamTokenOut>(`${IAM_API_PREFIX}/v1/auth/refresh`, {
                    method: 'POST',
                    data: { refresh_token: rawRefresh },
                    skipErrorHandler: true,
                  });
                  localStorage.setItem(STORAGE_BEARER_KEY, tok.access_token);
                  localStorage.setItem(STORAGE_REFRESH_TOKEN_KEY, tok.refresh_token);
                } catch {
                  localStorage.removeItem(STORAGE_BEARER_KEY);
                  localStorage.removeItem(STORAGE_REFRESH_TOKEN_KEY);
                  message.warning(formatMessage({ id: 'page.changePassword.refreshFailed' }));
                  history.replace(LOGIN_PATH);
                  return;
                }
              } else {
                localStorage.removeItem(STORAGE_BEARER_KEY);
                message.warning(formatMessage({ id: 'page.changePassword.noRefresh' }));
                history.replace(LOGIN_PATH);
                return;
              }
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
              authDebug('changePassword:done', { principal: currentUser.principal_label });
              await waitNextPaint();
              history.push('/overview/welcome');
            } catch (e) {
              const d = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
              if (typeof d === 'string') {
                setErr(d);
              } else {
                setErr(formatMessage({ id: 'page.changePassword.failed' }));
              }
            }
          }}
        >
          <ProFormText.Password
            name="current_password"
            fieldProps={{ size: 'large', prefix: <LockOutlined /> }}
            placeholder={formatMessage({ id: 'page.changePassword.currentPh' })}
            rules={[{ required: true, message: formatMessage({ id: 'page.changePassword.currentRequired' }) }]}
          />
          <ProFormText.Password
            name="new_password"
            fieldProps={{ size: 'large', prefix: <LockOutlined /> }}
            placeholder={formatMessage({ id: 'page.changePassword.newPh' })}
            rules={[
              { required: true, message: formatMessage({ id: 'page.changePassword.newRequired' }) },
              { min: 12, message: formatMessage({ id: 'page.changePassword.newMin' }) },
            ]}
          />
          <ProFormText.Password
            name="new_password2"
            fieldProps={{ size: 'large', prefix: <LockOutlined /> }}
            placeholder={formatMessage({ id: 'page.changePassword.confirmPh' })}
            rules={[{ required: true, message: formatMessage({ id: 'page.changePassword.confirmRequired' }) }]}
          />
        </LoginForm>
      </Card>
    </div>
  );
};

export default ChangePasswordPage;
