import { LockOutlined } from '@ant-design/icons';
import { LoginForm, ProFormText } from '@ant-design/pro-components';
import { history, Link, request, useModel } from '@umijs/max';
import { Alert, Card, theme, Typography } from 'antd';
import React, { useEffect, useMemo, useState } from 'react';

/** §十六-11：接受租户邀请（邮件内 token），必要时设置密码并建立会话。 */
const AcceptInvitePage: React.FC = () => {
  const { token } = theme.useToken();
  const { setInitialState } = useModel('@@initialState');
  const [err, setErr] = useState<string | null>(null);
  const urlToken = useMemo(() => new URLSearchParams(window.location.search).get('token') ?? '', []);

  useEffect(() => {
    void request('/api/v1/auth/csrf', { method: 'GET', skipErrorHandler: true });
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
        <div style={{ marginBottom: 16, textAlign: 'center' }}>
          <h1 style={{ margin: 0, fontSize: 22 }}>接受租户邀请</h1>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            若尚无账号，请设置登录密码（≥12 位）。若已登录为被邀请邮箱，可留空密码。
          </Typography.Paragraph>
        </div>
        {!urlToken ? (
          <Alert type="warning" showIcon message="链接缺少 token 参数" />
        ) : null}
        {err ? <Alert type="error" showIcon message={err} style={{ marginBottom: 16 }} closable onClose={() => setErr(null)} /> : null}
        <LoginForm
          submitter={{ searchConfig: { submitText: '接受并进入' } }}
          onFinish={async (values) => {
            if (!urlToken) {
              setErr('无效的邀请链接');
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
              setErr(typeof d === 'string' ? d : '无法接受邀请');
            }
          }}
        >
          <ProFormText.Password
            name="password"
            fieldProps={{ size: 'large', prefix: <LockOutlined /> }}
            placeholder="新密码（可选，已登录同邮箱可留空）"
          />
        </LoginForm>
        <Typography.Paragraph type="secondary" style={{ marginTop: 16, marginBottom: 0 }}>
          <Link to="/user/login">返回登录</Link>
        </Typography.Paragraph>
      </Card>
    </div>
  );
};

export default AcceptInvitePage;
