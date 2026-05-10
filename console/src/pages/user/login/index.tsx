import { LockOutlined } from '@ant-design/icons';
import { LoginForm, ProFormText } from '@ant-design/pro-components';
import { history, request, useModel } from '@umijs/max';
import { Alert, Card, theme } from 'antd';
import React, { useState } from 'react';

import { STORAGE_BEARER_KEY } from '@/constants/storage';

const Login: React.FC = () => {
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
      <Card style={{ width: 'min(420px, 100%)' }} bordered={false}>
        <div style={{ marginBottom: 24, textAlign: 'center' }}>
          <h1 style={{ margin: 0, fontSize: 22 }}>DeVault</h1>
          <p style={{ marginTop: 8, color: token.colorTextSecondary, marginBottom: 0 }}>
            使用 API Token / OIDC Bearer（与 REST 一致，非浏览器 Basic 弹窗）
          </p>
        </div>
        {err ? (
          <Alert type="error" showIcon message={err} style={{ marginBottom: 16 }} closable onClose={() => setErr(null)} />
        ) : null}
        <LoginForm
          submitter={{ searchConfig: { submitText: '登录' } }}
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
              await setInitialState((s) => ({
                ...s,
                currentUser,
                canAdmin: currentUser.role === 'admin',
                canWrite: currentUser.role === 'admin' || currentUser.role === 'operator',
              }));
              const sp = new URLSearchParams(window.location.search);
              const redirect = sp.get('redirect');
              const safe =
                redirect &&
                redirect.startsWith('/') &&
                !redirect.startsWith('//') &&
                !redirect.includes(':');
              history.push(safe ? redirect : '/overview/welcome');
            } catch (e) {
              localStorage.removeItem(STORAGE_BEARER_KEY);
              const status = (e as { response?: { status?: number; data?: { detail?: string } } })?.response
                ?.status;
              const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
              if (status === 401 || status === 403) {
                setErr(typeof detail === 'string' ? detail : 'Token 无效或无权访问');
              } else {
                setErr('无法连接控制面，请确认已启动 API 且开发代理指向正确端口');
              }
            }
          }}
        >
          <ProFormText.Password
            name="token"
            fieldProps={{ size: 'large', prefix: <LockOutlined /> }}
            placeholder="粘贴 Bearer Token（保存于本机 localStorage）"
            rules={[{ required: true, message: '请输入 Token' }]}
          />
        </LoginForm>
      </Card>
    </div>
  );
};

export default Login;
