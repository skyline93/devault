import { LockOutlined, SafetyCertificateOutlined, UserOutlined } from '@ant-design/icons';
import { LoginForm, ProFormText } from '@ant-design/pro-components';
import { history, Link, request, useIntl, useModel } from '@umijs/max';
import { Alert, Card, theme, Typography } from 'antd';
import React, { useRef, useState } from 'react';

import { STORAGE_BEARER_KEY, STORAGE_REFRESH_TOKEN_KEY } from '@/constants/storage';
import { CHANGE_PASSWORD_PATH } from '@/constants/auth-routes';
import { IAM_API_PREFIX, isIamConsoleEnabled } from '@/config/iam';
import { authDebug } from '@/utils/auth-debug';
import { computeSessionAccessFlags, setPasswordChangePending } from '@/utils/auth-access';
import { waitNextPaint } from '@/utils/wait-next-paint';

/** 本地 / 演示栈默认平台账号（与 deploy `DEMO_STACK_PLATFORM_*` 对齐，仅省开发输入）。 */
const DEFAULT_LOGIN_EMAIL = 'demo@devault.com';
const DEFAULT_LOGIN_PASSWORD = 'Devault12345';

type IamTokenOut = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  /** 平台管理员 JWT 可能为 `null` / 省略 */
  tenant_id?: string | null;
  permissions: string[];
  /** IAM：管理员创建账户后需改密 */
  must_change_password?: boolean;
};

const Login: React.FC = () => {
  const { formatMessage } = useIntl();
  const { token } = theme.useToken();
  const { setInitialState } = useModel('@@initialState');
  const [err, setErr] = useState<string | null>(null);
  const [mfaStep, setMfaStep] = useState(false);
  const [pendingIam, setPendingIam] = useState<{ email: string; password: string } | null>(null);
  const authSubmitLock = useRef(false);

  const finishLogin = async (currentUser: API.CurrentUser) => {
    const flags = computeSessionAccessFlags(currentUser);
    authDebug('finishLogin:beforeSetInitialState', {
      pathname: window.location.pathname,
      principal: currentUser.principal_label,
      hasBearer: Boolean(localStorage.getItem(STORAGE_BEARER_KEY)),
    });
    await setInitialState((s) => ({
      ...s,
      currentUser,
      canAdmin: flags.canAdmin,
      canWrite: flags.canWrite,
      canInviteMembers: flags.canInviteMembers,
      needsPasswordChange: flags.needsPasswordChange,
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
    if (authSubmitLock.current) {
      authDebug('loginViaIam:skippedDuplicate', {});
      return;
    }
    authSubmitLock.current = true;
    try {
      const data: Record<string, string> = { email, password };
      if (mfaCode) data.mfa_code = mfaCode;
      const tok = await request<IamTokenOut>(`${IAM_API_PREFIX}/v1/auth/login`, {
        method: 'POST',
        data,
        skipErrorHandler: true,
      });
      localStorage.setItem(STORAGE_BEARER_KEY, tok.access_token);
      localStorage.setItem(STORAGE_REFRESH_TOKEN_KEY, tok.refresh_token);
      authDebug('loginViaIam:afterIamLogin', { tenantId: tok.tenant_id, mustChangePassword: tok.must_change_password });
      if (tok.must_change_password) {
        setPasswordChangePending(true);
        setPendingIam(null);
        history.push(CHANGE_PASSWORD_PATH);
        return;
      }
      setPasswordChangePending(false);
      const currentUser = await request<API.CurrentUser>('/api/v1/auth/session', {
        method: 'GET',
        skipErrorHandler: true,
      });
      authDebug('loginViaIam:afterDevaultSession', { principal: currentUser.principal_label });
      setPendingIam(null);
      await finishLogin(currentUser);
    } finally {
      authSubmitLock.current = false;
    }
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
            {isIamConsoleEnabled()
              ? formatMessage({ id: 'page.login.subtitleIam' })
              : formatMessage({ id: 'page.login.subtitleCookie' })}
          </p>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0, marginTop: 8 }}>
            <Link to="/user/integration">{formatMessage({ id: 'page.login.linkIntegration' })}</Link>
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
              message={formatMessage({ id: 'page.login.mfaInfo' })}
              style={{ marginBottom: 16 }}
            />
            <LoginForm
              submitter={{ searchConfig: { submitText: formatMessage({ id: 'page.login.verify' }) } }}
              onFinish={async (values) => {
                const code = (values as { code?: string }).code?.trim();
                if (!code) {
                  setErr(formatMessage({ id: 'page.login.totpRequired' }));
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
                  setErr(typeof d === 'string' ? d : formatMessage({ id: 'page.login.verifyFailed' }));
                }
              }}
            >
              <ProFormText
                name="code"
                fieldProps={{ size: 'large', prefix: <SafetyCertificateOutlined /> }}
                placeholder={formatMessage({ id: 'page.login.mfaPlaceholder' })}
                rules={[{ required: true, message: formatMessage({ id: 'page.login.totpRequired' }) }]}
              />
            </LoginForm>
          </>
        ) : (
          <LoginForm
            initialValues={{ email: DEFAULT_LOGIN_EMAIL, password: DEFAULT_LOGIN_PASSWORD }}
            submitter={{ searchConfig: { submitText: formatMessage({ id: 'page.login.signIn' }) } }}
            onFinish={async (values) => {
              const email = (values as { email?: string }).email?.trim();
              const password = (values as { password?: string }).password;
              if (!email || !password) {
                setErr(formatMessage({ id: 'page.login.emailPasswordRequired' }));
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
                    setErr(typeof detail === 'string' ? detail : formatMessage({ id: 'page.login.badCredentials' }));
                  } else {
                    setErr(formatMessage({ id: 'page.login.networkIdentity' }));
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
                localStorage.removeItem(STORAGE_REFRESH_TOKEN_KEY);
                if (currentUser.needs_mfa) {
                  await setInitialState((s) => ({
                    ...s,
                    currentUser,
                    canAdmin: false,
                    canWrite: false,
                    canInviteMembers: false,
                    needsPasswordChange: computeSessionAccessFlags(currentUser).needsPasswordChange,
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
                  setErr(typeof detail === 'string' ? detail : formatMessage({ id: 'page.login.badCredentials' }));
                } else {
                  setErr(formatMessage({ id: 'page.login.networkControlPlane' }));
                }
              }
            }}
          >
            <ProFormText
              name="email"
              fieldProps={{ size: 'large', prefix: <UserOutlined /> }}
              placeholder={formatMessage({ id: 'page.login.email' })}
              rules={[{ required: true, message: formatMessage({ id: 'page.login.emailRequired' }) }]}
            />
            <ProFormText.Password
              name="password"
              fieldProps={{ size: 'large', prefix: <LockOutlined /> }}
              placeholder={formatMessage({ id: 'page.login.password' })}
              rules={[{ required: true, message: formatMessage({ id: 'page.login.passwordRequired' }) }]}
            />
          </LoginForm>
        )}
      </Card>
    </div>
  );
};

export default Login;
