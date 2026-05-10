import { LockOutlined, UserOutlined } from '@ant-design/icons';
import { LoginForm, ProFormText } from '@ant-design/pro-components';
import { Link, request } from '@umijs/max';
import { Alert, Card, theme, Typography } from 'antd';
import React, { useState } from 'react';

/** §十六-08：自助注册（需控制面 `DEVAULT_CONSOLE_SELF_REGISTRATION_ENABLED=true`）。 */
const SelfRegister: React.FC = () => {
  const { token } = theme.useToken();
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
          成功后需平台管理员分配租户成员资格。返回 <Link to="/user/login">密码登录</Link>
        </Typography.Paragraph>
        {ok ? <Alert type="success" message={ok} style={{ marginBottom: 16 }} /> : null}
        {err ? <Alert type="error" message={err} style={{ marginBottom: 16 }} /> : null}
        <LoginForm
          submitter={{ searchConfig: { submitText: '注册' } }}
          onFinish={async (values) => {
            setErr(null);
            setOk(null);
            try {
              await request('/api/v1/auth/register', {
                method: 'POST',
                data: {
                  email: (values as { email?: string }).email?.trim(),
                  password: (values as { password?: string }).password,
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
