import { LockOutlined } from '@ant-design/icons';
import { LoginForm, ProFormText } from '@ant-design/pro-components';
import { history, Link, request, useModel } from '@umijs/max';
import { Alert, Card, theme, Typography } from 'antd';
import React, { useState } from 'react';

import { STORAGE_BEARER_KEY } from '@/constants/storage';

/** IAM / 自动化 Bearer 入口（与密码登录页分离）。留空可在控制面未配置 IAM 时以 dev-open 进入（仅本地）。 */
const ApiIntegrationLogin: React.FC = () => {
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
          <h1 style={{ margin: 0, fontSize: 22 }}>Bearer 登录</h1>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            粘贴 IAM 下发的 <code>access_token</code> 写入本机 <code>localStorage</code>；人机主路径请使用{' '}
            <Link to="/user/login">IAM 登录</Link>。留空仅在控制面未配置 <code>DEVAULT_IAM_JWT_*</code>（dev-open）时可用。
          </Typography.Paragraph>
        </div>
        {err ? <Alert type="error" showIcon message={err} style={{ marginBottom: 16 }} closable onClose={() => setErr(null)} /> : null}
        <LoginForm
          submitter={{ searchConfig: { submitText: '验证并进入' } }}
          onFinish={async (values) => {
            const raw = (values as { token?: string }).token?.trim() ?? '';
            setErr(null);
            if (raw) {
              localStorage.setItem(STORAGE_BEARER_KEY, raw);
            } else {
              localStorage.removeItem(STORAGE_BEARER_KEY);
            }
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
            placeholder="IAM access_token（可留空 = dev-open）"
          />
        </LoginForm>
      </Card>
    </div>
  );
};

export default ApiIntegrationLogin;
