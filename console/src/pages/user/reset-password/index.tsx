import { LockOutlined } from '@ant-design/icons';
import { LoginForm, ProFormText } from '@ant-design/pro-components';
import { history, Link, request, useIntl } from '@umijs/max';
import { Alert, Card, theme, Typography } from 'antd';
import React, { useMemo, useState } from 'react';

const ResetPassword: React.FC = () => {
  const { formatMessage } = useIntl();
  const { token } = theme.useToken();
  const [err, setErr] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const urlToken = useMemo(() => {
    const q = new URLSearchParams(window.location.search).get('token');
    return q?.trim() || '';
  }, []);

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
        <Typography.Title level={4}>{formatMessage({ id: 'page.resetPassword.title' })}</Typography.Title>
        <Typography.Paragraph type="secondary">
          <Link to="/user/login">{formatMessage({ id: 'page.resetPassword.back' })}</Link>
        </Typography.Paragraph>
        {!urlToken ? (
          <Alert type="warning" message={formatMessage({ id: 'page.resetPassword.missingToken' })} />
        ) : done ? (
          <Alert type="success" message={formatMessage({ id: 'page.resetPassword.success' })} />
        ) : (
          <>
            {err ? <Alert type="error" message={err} style={{ marginBottom: 16 }} /> : null}
            <LoginForm
              submitter={{ searchConfig: { submitText: formatMessage({ id: 'page.resetPassword.submit' }) } }}
              onFinish={async (values) => {
                setErr(null);
                const np = (values as { new_password?: string }).new_password;
                if (!np || np.length < 12) {
                  setErr(formatMessage({ id: 'page.resetPassword.short' }));
                  return;
                }
                try {
                  await request('/api/v1/auth/password-reset/confirm', {
                    method: 'POST',
                    data: { token: urlToken, new_password: np },
                    skipErrorHandler: true,
                  });
                  setDone(true);
                  setTimeout(() => history.push('/user/login'), 2000);
                } catch (e) {
                  const d = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
                  setErr(typeof d === 'string' ? d : formatMessage({ id: 'page.resetPassword.failed' }));
                }
              }}
            >
              <ProFormText.Password
                name="new_password"
                fieldProps={{ prefix: <LockOutlined /> }}
                placeholder={formatMessage({ id: 'page.resetPassword.newPasswordPh' })}
                rules={[{ required: true, min: 12 }]}
              />
            </LoginForm>
          </>
        )}
      </Card>
    </div>
  );
};

export default ResetPassword;
