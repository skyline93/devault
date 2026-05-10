import { LockOutlined, SafetyCertificateOutlined, UserOutlined } from '@ant-design/icons';
import { LoginForm, ProFormText } from '@ant-design/pro-components';
import { history, Link, request, useModel } from '@umijs/max';
import { Alert, Card, theme, Typography } from 'antd';
import React, { useEffect, useState } from 'react';

import { STORAGE_BEARER_KEY } from '@/constants/storage';

const Login: React.FC = () => {
  const { token } = theme.useToken();
  const { setInitialState } = useModel('@@initialState');
  const [err, setErr] = useState<string | null>(null);
  const [mfaStep, setMfaStep] = useState(false);

  useEffect(() => {
    void request('/api/v1/auth/csrf', { method: 'GET', skipErrorHandler: true });
  }, []);

  const finishLogin = async (currentUser: API.CurrentUser) => {
    const canWrite = !currentUser.needs_mfa && (currentUser.role === 'admin' || currentUser.role === 'operator');
    const canAdmin = !currentUser.needs_mfa && currentUser.role === 'admin';
    await setInitialState((s) => ({
      ...s,
      currentUser,
      canAdmin,
      canWrite,
      canInviteMembers: Boolean(
        currentUser.tenants?.some((t) => t.membership_role === 'tenant_admin'),
      ),
    }));
    const sp = new URLSearchParams(window.location.search);
    const redirect = sp.get('redirect');
    const safe =
      redirect && redirect.startsWith('/') && !redirect.startsWith('//') && !redirect.includes(':');
    history.push(safe ? redirect : '/overview/welcome');
  };

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
          <h1 style={{ margin: 0, fontSize: 22 }}>DeVault</h1>
          <p style={{ marginTop: 8, color: token.colorTextSecondary, marginBottom: 0 }}>
            人机主路径：<strong>邮箱 + 密码</strong>（Cookie 会话）
          </p>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0, marginTop: 8 }}>
            <Link to="/user/integration">API Token / 机器集成</Link>
            {' · '}
            <Link to="/user/register">自助注册</Link>
          </Typography.Paragraph>
        </div>
        {err ? (
          <Alert type="error" showIcon message={err} style={{ marginBottom: 16 }} closable onClose={() => setErr(null)} />
        ) : null}

        {mfaStep ? (
          <>
            <Alert
              type="info"
              showIcon
              message="请输入验证器中的 6 位动态码"
              style={{ marginBottom: 16 }}
            />
            <LoginForm
              submitter={{ searchConfig: { submitText: '验证' } }}
              onFinish={async (values) => {
                const code = (values as { code?: string }).code?.trim();
                if (!code) {
                  setErr('请输入动态码');
                  return;
                }
                setErr(null);
                try {
                  const currentUser = await request<API.CurrentUser>('/api/v1/auth/mfa/verify', {
                    method: 'POST',
                    data: { code },
                    skipErrorHandler: true,
                  });
                  await finishLogin(currentUser);
                } catch (e) {
                  const d = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
                  setErr(typeof d === 'string' ? d : '验证失败');
                }
              }}
            >
              <ProFormText
                name="code"
                fieldProps={{ size: 'large', prefix: <SafetyCertificateOutlined /> }}
                placeholder="TOTP 动态码"
                rules={[{ required: true, message: '请输入动态码' }]}
              />
            </LoginForm>
          </>
        ) : (
          <LoginForm
            submitter={{ searchConfig: { submitText: '登录' } }}
            onFinish={async (values) => {
              const email = (values as { email?: string }).email?.trim();
              const password = (values as { password?: string }).password;
              if (!email || !password) {
                setErr('请输入邮箱与密码');
                return;
              }
              setErr(null);
              try {
                const currentUser = await request<API.CurrentUser>('/api/v1/auth/login', {
                  method: 'POST',
                  data: { email, password },
                  skipErrorHandler: true,
                });
                localStorage.removeItem(STORAGE_BEARER_KEY);
                if (currentUser.needs_mfa) {
                  await setInitialState((s) => ({
                    ...s,
                    currentUser,
                    canAdmin: false,
                    canWrite: false,
                    canInviteMembers: false,
                  }));
                  setMfaStep(true);
                  return;
                }
                await finishLogin(currentUser);
              } catch (e) {
                const status = (e as { response?: { status?: number; data?: { detail?: string } } })?.response
                  ?.status;
                const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
                if (status === 401 || status === 403) {
                  setErr(typeof detail === 'string' ? detail : '邮箱或密码错误');
                } else {
                  setErr('无法连接控制面，请确认已启动 API 且开发代理指向正确端口');
                }
              }
            }}
          >
            <ProFormText
              name="email"
              fieldProps={{ size: 'large', prefix: <UserOutlined /> }}
              placeholder="邮箱"
              rules={[{ required: true, message: '请输入邮箱' }]}
            />
            <ProFormText.Password
              name="password"
              fieldProps={{ size: 'large', prefix: <LockOutlined /> }}
              placeholder="密码"
              rules={[{ required: true, message: '请输入密码' }]}
            />
          </LoginForm>
        )}
      </Card>
    </div>
  );
};

export default Login;
