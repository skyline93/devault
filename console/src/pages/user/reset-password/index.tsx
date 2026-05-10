import { LockOutlined } from '@ant-design/icons';
import { LoginForm, ProFormText } from '@ant-design/pro-components';
import { history, Link, request } from '@umijs/max';
import { Alert, Card, theme, Typography } from 'antd';
import React, { useMemo, useState } from 'react';

/** §十六-10：通过邮件中的 token 重置密码。 */
const ResetPassword: React.FC = () => {
  const { token } = theme.useToken();
  const [err, setErr] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const urlToken = useMemo(() => {
    const q = new URLSearchParams(window.location.search).get('token');
    return q?.trim() || '';
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
        <Typography.Title level={4}>重置密码</Typography.Title>
        <Typography.Paragraph type="secondary">
          <Link to="/user/login">返回登录</Link>
        </Typography.Paragraph>
        {!urlToken ? (
          <Alert type="warning" message="链接缺少 token 参数" />
        ) : done ? (
          <Alert type="success" message="密码已更新，请使用新密码登录。" />
        ) : (
          <>
            {err ? <Alert type="error" message={err} style={{ marginBottom: 16 }} /> : null}
            <LoginForm
              submitter={{ searchConfig: { submitText: '保存新密码' } }}
              onFinish={async (values) => {
                setErr(null);
                const np = (values as { new_password?: string }).new_password;
                if (!np || np.length < 12) {
                  setErr('新密码至少 12 位');
                  return;
                }
                try {
                  await request('/api/v1/auth/password-reset/confirm', {
                    method: 'POST',
                    data: { token: urlToken, new_password: np },
                    skipErrorHandler: true,
                  });
                  setDone(true);
                  setTimeout(() => history.push('/user/login'), 2000);
                } catch (e) {
                  const d = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
                  setErr(typeof d === 'string' ? d : '链接无效或已过期');
                }
              }}
            >
              <ProFormText.Password
                name="new_password"
                fieldProps={{ prefix: <LockOutlined /> }}
                placeholder="新密码（≥12 位）"
                rules={[{ required: true, min: 12 }]}
              />
            </LoginForm>
          </>
        )}
      </Card>
    </div>
  );
};

export default ResetPassword;
