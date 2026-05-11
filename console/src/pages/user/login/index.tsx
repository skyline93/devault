import { LockOutlined, SafetyCertificateOutlined, UserOutlined } from '@ant-design/icons';
import { LoginForm, ProFormText } from '@ant-design/pro-components';
import { history, Link, request, useModel } from '@umijs/max';
import { Alert, Card, theme, Typography } from 'antd';
import React, { useState } from 'react';

import { STORAGE_BEARER_KEY } from '@/constants/storage';
import { IAM_API_PREFIX, isIamConsoleEnabled } from '@/config/iam';
import { authDebug } from '@/utils/auth-debug';
import { waitNextPaint } from '@/utils/wait-next-paint';

type IamTokenOut = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  tenant_id: string;
  permissions: string[];
};

const Login: React.FC = () => {
  const { token } = theme.useToken();
  const { setInitialState } = useModel('@@initialState');
  const [err, setErr] = useState<string | null>(null);
  const [mfaStep, setMfaStep] = useState(false);
  const [pendingIam, setPendingIam] = useState<{ email: string; password: string } | null>(null);

  const finishLogin = async (currentUser: API.CurrentUser) => {
    const canWrite = !currentUser.needs_mfa && (currentUser.role === 'admin' || currentUser.role === 'operator');
    const canAdmin = !currentUser.needs_mfa && currentUser.role === 'admin';
    authDebug('finishLogin:beforeSetInitialState', {
      pathname: window.location.pathname,
      principal: currentUser.principal_label,
      hasBearer: Boolean(localStorage.getItem(STORAGE_BEARER_KEY)),
    });
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
    const target = safe ? redirect : '/overview/welcome';
    authDebug('finishLogin:afterSetInitialState', { target });
    await waitNextPaint();
    authDebug('finishLogin:beforeHistoryPush', { target });
    history.push(target);
  };

  const loginViaIam = async (email: string, password: string, mfaCode?: string) => {
    const data: Record<string, string> = { email, password };
    if (mfaCode) data.mfa_code = mfaCode;
    const tok = await request<IamTokenOut>(`${IAM_API_PREFIX}/v1/auth/login`, {
      method: 'POST',
      data,
      skipErrorHandler: true,
    });
    localStorage.setItem(STORAGE_BEARER_KEY, tok.access_token);
    authDebug('loginViaIam:afterIamLogin', { tenantId: tok.tenant_id });
    const currentUser = await request<API.CurrentUser>('/api/v1/auth/session', {
      method: 'GET',
      skipErrorHandler: true,
    });
    authDebug('loginViaIam:afterDevaultSession', { principal: currentUser.principal_label });
    setPendingIam(null);
    await finishLogin(currentUser);
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
            {isIamConsoleEnabled() ? (
              <>
                已通过 <strong>独立 IAM</strong> 登录（Bearer + DeVault 会话接口）
              </>
            ) : (
              <>
                人机主路径：<strong>邮箱 + 密码</strong>（Cookie 会话）
              </>
            )}
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
                  if (isIamConsoleEnabled() && pendingIam) {
                    await loginViaIam(pendingIam.email, pendingIam.password, code);
                    return;
                  }
                  const currentUser = await request<API.CurrentUser>('/api/v1/auth/mfa/verify', {
                    method: 'POST',
                    data: { code },
                    skipErrorHandler: true,
                  });
                  await finishLogin(currentUser);
                } catch (e) {
                  const d = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
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
              if (isIamConsoleEnabled()) {
                try {
                  await loginViaIam(email, password);
                } catch (e) {
                  const status = (e as { response?: { status?: number; data?: { detail?: unknown } } })?.response
                    ?.status;
                  const detail = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
                  if (
                    status === 403 &&
                    detail &&
                    typeof detail === 'object' &&
                    'code' in detail &&
                    (detail as { code?: string }).code === 'mfa_required'
                  ) {
                    setPendingIam({ email, password });
                    setMfaStep(true);
                    return;
                  }
                  if (status === 401 || status === 403) {
                    setErr(typeof detail === 'string' ? detail : '邮箱或密码错误');
                  } else {
                    setErr('无法连接 IAM 或控制面，请确认 IAM / API 已启动且代理正确');
                  }
                }
                return;
              }
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
