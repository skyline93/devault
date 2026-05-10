import { LockOutlined } from '@ant-design/icons';
import { LoginForm, ProFormText } from '@ant-design/pro-components';
import { history, Link, request, useModel } from '@umijs/max';
import { Alert, Card, theme, Typography } from 'antd';
import React, { useEffect, useState } from 'react';

import { STORAGE_BEARER_KEY } from '@/constants/storage';

/** §十六-07：API 密钥 / 机器集成入口（与密码登录页分离）。 */
const ApiIntegrationLogin: React.FC = () => {
  const { token } = theme.useToken();
  const { setInitialState } = useModel('@@initialState');
  const [err, setErr] = useState<string | null>(null);

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
          <h1 style={{ margin: 0, fontSize: 22 }}>API Token 登录</h1>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            将 Bearer 写入本机 <code>localStorage</code>，用于自动化与应急；人机主路径请使用{' '}
            <Link to="/user/login">邮箱 + 密码</Link>。
          </Typography.Paragraph>
        </div>
        {err ? <Alert type="error" showIcon message={err} style={{ marginBottom: 16 }} closable onClose={() => setErr(null)} /> : null}
        <LoginForm
          submitter={{ searchConfig: { submitText: '验证并进入' } }}
          onFinish={async (values) => {
            const raw = (values as { token?: string }).token?.trim();
            if (!raw) {
              setErr('请输入 Token');
              return;
            }
            setErr(null);
            localStorage.setItem(STORAGE_BEARER_KEY, raw);
            try {
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
            } catch (e) {
              localStorage.removeItem(STORAGE_BEARER_KEY);
              const status = (e as { response?: { status?: number } })?.response?.status;
              setErr(status === 401 || status === 403 ? 'Token 无效或无权访问' : '无法连接控制面');
            }
          }}
        >
          <ProFormText.Password
            name="token"
            fieldProps={{ size: 'large', prefix: <LockOutlined /> }}
            placeholder="Bearer Token"
            rules={[{ required: true, message: '请输入 Token' }]}
          />
        </LoginForm>
      </Card>
    </div>
  );
};

export default ApiIntegrationLogin;
