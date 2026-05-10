import { LockOutlined, UserOutlined } from '@ant-design/icons';
import { LoginForm, ProFormText } from '@ant-design/pro-components';
import { history, Link, request, useModel } from '@umijs/max';
import { Alert, Card, theme, Typography } from 'antd';
import React, { useState } from 'react';

import { STORAGE_BEARER_KEY } from '@/constants/storage';
import { IAM_API_PREFIX, isIamConsoleEnabled } from '@/config/iam';

type IamTokenOut = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  tenant_id: string;
  permissions: string[];
};

/** 自助注册：IAM 模式下走 IAM API；否则为历史占位（控制面不再提供 `/auth/register`）。 */
const SelfRegister: React.FC = () => {
  const { token } = theme.useToken();
  const { setInitialState } = useModel('@@initialState');
  const [ok, setOk] = useState<string | null>(null);
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
        <Typography.Title level={4} style={{ textAlign: 'center' }}>
          注册控制台账号
        </Typography.Title>
        <Typography.Paragraph type="secondary" style={{ textAlign: 'center' }}>
          {isIamConsoleEnabled() ? (
            <>使用独立 IAM 注册后将直接进入控制台（需 DeVault 已配置 <code>DEVAULT_IAM_JWT_*</code>）。 </>
          ) : (
            <>成功后需平台管理员分配租户成员资格。 </>
          )}
          返回 <Link to="/user/login">密码登录</Link>
        </Typography.Paragraph>
        {ok ? <Alert type="success" message={ok} style={{ marginBottom: 16 }} /> : null}
        {err ? <Alert type="error" message={err} style={{ marginBottom: 16 }} /> : null}
        <LoginForm
          submitter={{ searchConfig: { submitText: '注册' } }}
          onFinish={async (values) => {
            setErr(null);
            setOk(null);
            const email = (values as { email?: string }).email?.trim();
            const password = (values as { password?: string }).password;
            if (!email || !password) {
              setErr('请输入邮箱与密码');
              return;
            }
            try {
              if (isIamConsoleEnabled()) {
                const tok = await request<IamTokenOut>(`${IAM_API_PREFIX}/v1/auth/register`, {
                  method: 'POST',
                  data: {
                    email,
                    password,
                    name: email.split('@')[0] || 'user',
                  },
                  skipErrorHandler: true,
                });
                localStorage.setItem(STORAGE_BEARER_KEY, tok.access_token);
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
                return;
              }
              await request('/api/v1/auth/register', {
                method: 'POST',
                data: {
                  email,
                  password,
                },
                skipErrorHandler: true,
              });
              setOk('账号已创建。请联系管理员分配租户权限后使用密码登录。');
            } catch (e) {
              const st = (e as { response?: { status?: number; data?: { detail?: string } } })?.response?.status;
              const d = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
              if (st === 403) setErr(typeof d === 'string' ? d : '未开放自助注册');
              else if (st === 409) setErr('该邮箱已注册');
              else setErr(typeof d === 'string' ? d : '注册失败');
            }
          }}
        >
          <ProFormText
            name="email"
            fieldProps={{ prefix: <UserOutlined /> }}
            placeholder="邮箱"
            rules={[{ required: true }]}
          />
          <ProFormText.Password
            name="password"
            fieldProps={{ prefix: <LockOutlined /> }}
            placeholder="密码（至少 12 位）"
            rules={[{ required: true, min: 12 }]}
          />
        </LoginForm>
      </Card>
    </div>
  );
};

export default SelfRegister;
