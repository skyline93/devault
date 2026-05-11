import { LockOutlined } from '@ant-design/icons';
import { LoginForm, ProFormText } from '@ant-design/pro-components';
import { history, Link, request, useIntl, useModel } from '@umijs/max';
import { Alert, Card, theme, Typography } from 'antd';
import React, { useMemo, useState } from 'react';

const AcceptInvitePage: React.FC = () => {
  const { formatMessage } = useIntl();
  const { token } = theme.useToken();
  const { setInitialState } = useModel('@@initialState');
  const [err, setErr] = useState<string | null>(null);
  const urlToken = useMemo(() => new URLSearchParams(window.location.search).get('token') ?? '', []);

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
          <h1 style={{ margin: 0, fontSize: 22 }}>{formatMessage({ id: 'page.acceptInvite.title' })}</h1>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            {formatMessage({ id: 'page.acceptInvite.subtitle' })}
          </Typography.Paragraph>
        </div>
        {!urlToken ? (
          <Alert type="warning" showIcon message={formatMessage({ id: 'page.acceptInvite.missingToken' })} />
        ) : null}
        {err ? <Alert type="error" showIcon message={err} style={{ marginBottom: 16 }} closable onClose={() => setErr(null)} /> : null}
        <LoginForm
          submitter={{ searchConfig: { submitText: formatMessage({ id: 'page.acceptInvite.submit' }) } }}
          onFinish={async (values) => {
            if (!urlToken) {
              setErr(formatMessage({ id: 'page.acceptInvite.invalid' }));
              return;
            }
            const pwd = (values as { password?: string }).password?.trim();
            setErr(null);
            try {
              const currentUser = await request<API.CurrentUser>('/api/v1/auth/invitations/accept', {
                method: 'POST',
                data: { token: urlToken, password: pwd || undefined },
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
            } catch (e) {
              const d = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
              setErr(typeof d === 'string' ? d : formatMessage({ id: 'page.acceptInvite.failed' }));
            }
          }}
        >
          <ProFormText.Password
            name="password"
            fieldProps={{ size: 'large', prefix: <LockOutlined /> }}
            placeholder={formatMessage({ id: 'page.acceptInvite.passwordPh' })}
          />
        </LoginForm>
        <Typography.Paragraph type="secondary" style={{ marginTop: 16, marginBottom: 0 }}>
          <Link to="/user/login">{formatMessage({ id: 'page.acceptInvite.backLogin' })}</Link>
        </Typography.Paragraph>
      </Card>
    </div>
  );
};

export default AcceptInvitePage;
