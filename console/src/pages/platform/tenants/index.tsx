import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { request } from '@umijs/max';
import { App, Button, Form, Input, Modal, Select, Switch, Typography, notification } from 'antd';
import React, { useRef, useState } from 'react';

import { detailFromError } from '@/requestErrorConfig';

const slugPattern = /^[a-z0-9]+(?:[-_][a-z0-9]+)*$/;

const TenantsAdminPage: React.FC = () => {
  const { message } = App.useApp();
  const actionRef = useRef<ActionType>();
  const [open, setOpen] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [row, setRow] = useState<API.TenantOut | null>(null);
  const [form] = Form.useForm();
  const [createForm] = Form.useForm();

  const columns: ProColumns<API.TenantOut>[] = [
    { title: '名称', dataIndex: 'name' },
    { title: 'slug', dataIndex: 'slug', copyable: true },
    { title: '强制加密制品', dataIndex: 'require_encrypted_artifacts', width: 120, render: (_, r) => (r.require_encrypted_artifacts ? '是' : '否') },
    {
      title: '管理员 MFA',
      dataIndex: 'require_mfa_for_admins',
      width: 110,
      render: (_, r) => (r.require_mfa_for_admins ? '是' : '否'),
    },
    { title: 'allowlist 模式', dataIndex: 'policy_paths_allowlist_mode', width: 120 },
    {
      title: '操作',
      valueType: 'option',
      width: 100,
      render: (_, r) => (
        <Button
          type="link"
          size="small"
          onClick={() => {
            setRow(r);
            form.setFieldsValue({
              name: r.name,
              require_encrypted_artifacts: r.require_encrypted_artifacts,
              require_mfa_for_admins: Boolean(r.require_mfa_for_admins),
              kms_envelope_key_id: r.kms_envelope_key_id ?? '',
              s3_bucket: r.s3_bucket ?? '',
              s3_assume_role_arn: r.s3_assume_role_arn ?? '',
              s3_assume_role_external_id: r.s3_assume_role_external_id ?? '',
              policy_paths_allowlist_mode: r.policy_paths_allowlist_mode,
              sso_oidc_issuer: r.sso_oidc_issuer ?? '',
              sso_oidc_audience: r.sso_oidc_audience ?? '',
              sso_oidc_role_claim: r.sso_oidc_role_claim ?? 'devault_role',
              sso_oidc_email_claim: r.sso_oidc_email_claim ?? 'email',
              sso_password_login_disabled: Boolean(r.sso_password_login_disabled),
              sso_jit_provisioning: Boolean(r.sso_jit_provisioning),
              sso_saml_entity_id: r.sso_saml_entity_id ?? '',
              sso_saml_acs_url: r.sso_saml_acs_url ?? '',
            });
            setOpen(true);
          }}
        >
          编辑
        </Button>
      ),
    },
  ];

  return (
    <PageContainer
      title="租户（平台管理员）"
      subTitle="租户不是单独一套登录账号：用户仍使用全局登录页；加入该租户成员关系后，可在顶栏「租户」里切换到新租户。"
    >
      <div style={{ marginBottom: 16 }}>
        <Button
          type="primary"
          onClick={() => {
            createForm.resetFields();
            setCreateOpen(true);
          }}
        >
          新建租户
        </Button>
      </div>

      <ProTable<API.TenantOut>
        rowKey="id"
        actionRef={actionRef}
        columns={columns}
        search={false}
        request={async () => {
          const data = await request<API.TenantOut[]>('/api/v1/tenants');
          return { data, success: true, total: data.length };
        }}
        pagination={{ pageSize: 20 }}
      />

      <Modal
        title="新建租户"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        destroyOnClose
        okText="创建"
        onOk={async () => {
          const v = await createForm.validateFields();
          const slug = String(v.slug ?? '')
            .trim()
            .toLowerCase();
          try {
            const created = await request<API.TenantOut>('/api/v1/tenants', {
              method: 'POST',
              data: { name: String(v.name ?? '').trim(), slug },
              skipErrorHandler: true,
            });
            setCreateOpen(false);
            await actionRef.current?.reload?.();
            message.success('租户已创建');
            notification.success({
              message: '租户已创建',
              duration: 14,
              description: (
                <div>
                  <p style={{ marginBottom: 8 }}>
                    <strong>如何「进入」该租户：</strong>DeVault 控制台是<strong>统一登录</strong>（同一邮箱/密码或
                    SSO）。用户<strong>不会</strong>按租户单独登录；需要先具备该租户的<strong>成员关系</strong>，再用顶栏
                    「租户」下拉框切换到「{created.name}」。
                  </p>
                  <p style={{ marginBottom: 8 }}>
                    <strong>添加成员：</strong>新租户一般还没有任何成员——请先在可访问数据库的主机上执行{' '}
                    <code>devault-admin create-console-user</code>，其中 <code>--tenant</code> 填下方复制的租户 ID，以绑定首名{' '}
                    <code>tenant_admin</code>；之后该用户用常规方式登录，并在顶栏选择本租户，再在「概览 → 成员邀请」邀请其他人。
                  </p>
                  <Typography.Text type="secondary">租户 ID（可点击复制）：</Typography.Text>
                  <Typography.Paragraph copyable style={{ marginBottom: 0 }} code>
                    {created.id}
                  </Typography.Paragraph>
                </div>
              ),
            });
          } catch (e) {
            message.error(detailFromError(e));
            throw e;
          }
        }}
      >
        <Form form={createForm} layout="vertical">
          <Form.Item name="name" label="显示名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="例如 Acme Corp" />
          </Form.Item>
          <Form.Item
            name="slug"
            label="slug（唯一标识）"
            rules={[
              { required: true, message: '请输入 slug' },
              { pattern: slugPattern, message: '仅小写字母、数字、连字符或下划线，且分隔处两侧须有字符' },
            ]}
            extra="提交时会转为小写；须全局唯一。"
          >
            <Input placeholder="例如 acme-corp" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={row ? `编辑租户 ${row.slug}` : ''}
        open={open}
        onCancel={() => setOpen(false)}
        okText="PATCH 保存"
        width={720}
        onOk={async () => {
          if (!row) return;
          const v = await form.validateFields();
          /** 空字符串可走服务端 strip→None 清空 BYOB/KMS 等可选字段。 */
          const body: Record<string, unknown> = {
            name: v.name,
            require_encrypted_artifacts: v.require_encrypted_artifacts,
            require_mfa_for_admins: v.require_mfa_for_admins,
            policy_paths_allowlist_mode: v.policy_paths_allowlist_mode,
            sso_password_login_disabled: v.sso_password_login_disabled,
            sso_jit_provisioning: v.sso_jit_provisioning,
          };
          const oiss = String(v.sso_oidc_issuer ?? '').trim();
          const oaud = String(v.sso_oidc_audience ?? '').trim();
          body.sso_oidc_issuer = oiss.length ? oiss : '';
          body.sso_oidc_audience = oaud.length ? oaud : '';
          body.sso_oidc_role_claim = String(v.sso_oidc_role_claim ?? 'devault_role').trim() || 'devault_role';
          body.sso_oidc_email_claim = String(v.sso_oidc_email_claim ?? 'email').trim() || 'email';
          const se = String(v.sso_saml_entity_id ?? '').trim();
          body.sso_saml_entity_id = se.length ? se : '';
          const sacs = String(v.sso_saml_acs_url ?? '').trim();
          body.sso_saml_acs_url = sacs.length ? sacs : '';
          const kms = String(v.kms_envelope_key_id ?? '').trim();
          body.kms_envelope_key_id = kms.length ? kms : '';
          const b = String(v.s3_bucket ?? '').trim();
          body.s3_bucket = b.length ? b : '';
          const arn = String(v.s3_assume_role_arn ?? '').trim();
          body.s3_assume_role_arn = arn.length ? arn : '';
          const ext = String(v.s3_assume_role_external_id ?? '').trim();
          body.s3_assume_role_external_id = ext.length ? ext : '';
          await request(`/api/v1/tenants/${row.id}`, { method: 'PATCH', data: body });
          message.success('已更新租户');
          setOpen(false);
          actionRef.current?.reload();
        }}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="require_encrypted_artifacts" label="require_encrypted_artifacts" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item
            name="require_mfa_for_admins"
            label="租户管理员须 TOTP（require_mfa_for_admins）"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
          <Form.Item name="kms_envelope_key_id" label="kms_envelope_key_id">
            <Input placeholder="留空则清空" />
          </Form.Item>
          <Form.Item name="s3_bucket" label="s3_bucket（BYOB）">
            <Input placeholder="留空则清空" />
          </Form.Item>
          <Form.Item name="s3_assume_role_arn" label="s3_assume_role_arn">
            <Input placeholder="留空则清空" />
          </Form.Item>
          <Form.Item name="s3_assume_role_external_id" label="s3_assume_role_external_id">
            <Input placeholder="留空则清空" />
          </Form.Item>
          <Form.Item name="policy_paths_allowlist_mode" label="policy_paths_allowlist_mode">
            <Select
              options={[
                { value: 'off', label: 'off' },
                { value: 'warn', label: 'warn' },
                { value: 'enforce', label: 'enforce' },
              ]}
            />
          </Form.Item>
          <Typography.Title level={5} style={{ marginTop: 16 }}>
            §十六-12 租户 OIDC / SAML 元数据
          </Typography.Title>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 8 }}>
            配置 <strong>issuer + audience</strong> 后，携带对应 IdP JWT 的 <code>Authorization: Bearer</code> 将解析为仅该租户作用域的主体；与全局{' '}
            <code>DEVAULT_OIDC_*</code> 并存时由 JWT 的 <code>iss</code>/<code>aud</code> 匹配租户行。
            <strong>SAML</strong> 下列字段仅作运维登记，控制面<strong>不消费</strong> SAML 断言。
          </Typography.Paragraph>
          <Form.Item name="sso_oidc_issuer" label="sso_oidc_issuer（OpenID issuer URL）">
            <Input placeholder="留空则清空 OIDC 绑定" />
          </Form.Item>
          <Form.Item name="sso_oidc_audience" label="sso_oidc_audience（JWT aud）">
            <Input placeholder="与 issuer 成对填写或同时留空" />
          </Form.Item>
          <Form.Item name="sso_oidc_role_claim" label="sso_oidc_role_claim">
            <Input />
          </Form.Item>
          <Form.Item name="sso_oidc_email_claim" label="sso_oidc_email_claim（JIT 用）">
            <Input />
          </Form.Item>
          <Form.Item name="sso_jit_provisioning" label="OIDC JIT 成员（sso_jit_provisioning）" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item
            name="sso_password_login_disabled"
            label="禁用该租户成员的邮箱密码登录（sso_password_login_disabled）"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
          <Form.Item name="sso_saml_entity_id" label="sso_saml_entity_id（登记用）">
            <Input placeholder="可选" />
          </Form.Item>
          <Form.Item name="sso_saml_acs_url" label="sso_saml_acs_url（登记用）">
            <Input placeholder="可选" />
          </Form.Item>
        </Form>
      </Modal>
    </PageContainer>
  );
};

export default TenantsAdminPage;
