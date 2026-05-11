import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { request, useIntl } from '@umijs/max';
import { App, Button, Form, Input, Modal, Select, Switch, Typography, notification } from 'antd';
import React, { useMemo, useRef, useState } from 'react';

import { detailFromError } from '@/requestErrorConfig';

const slugPattern = /^[a-z0-9]+(?:[-_][a-z0-9]+)*$/;

const TenantsAdminPage: React.FC = () => {
  const { formatMessage } = useIntl();
  const { message } = App.useApp();
  const actionRef = useRef<ActionType>();
  const [open, setOpen] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [row, setRow] = useState<API.TenantOut | null>(null);
  const [form] = Form.useForm();
  const [createForm] = Form.useForm();

  const columns: ProColumns<API.TenantOut>[] = useMemo(
    () => [
      { title: formatMessage({ id: 'page.tenants.colName' }), dataIndex: 'name' },
      { title: formatMessage({ id: 'page.tenants.colSlug' }), dataIndex: 'slug', copyable: true },
      {
        title: formatMessage({ id: 'page.tenants.colEncrypted' }),
        dataIndex: 'require_encrypted_artifacts',
        width: 120,
        render: (_, r) =>
          r.require_encrypted_artifacts ? formatMessage({ id: 'page.tenants.yes' }) : formatMessage({ id: 'page.tenants.no' }),
      },
      {
        title: formatMessage({ id: 'page.tenants.colMfaAdmins' }),
        dataIndex: 'require_mfa_for_admins',
        width: 110,
        render: (_, r) =>
          r.require_mfa_for_admins ? formatMessage({ id: 'page.tenants.yes' }) : formatMessage({ id: 'page.tenants.no' }),
      },
      { title: formatMessage({ id: 'page.tenants.colAllowlist' }), dataIndex: 'policy_paths_allowlist_mode', width: 120 },
      {
        title: formatMessage({ id: 'page.tenants.colActions' }),
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
            {formatMessage({ id: 'page.tenants.edit' })}
          </Button>
        ),
      },
    ],
    [formatMessage, form],
  );

  return (
    <PageContainer title={formatMessage({ id: 'page.tenants.title' })} subTitle={formatMessage({ id: 'page.tenants.subtitle' })}>
      <div style={{ marginBottom: 16 }}>
        <Button
          type="primary"
          onClick={() => {
            createForm.resetFields();
            setCreateOpen(true);
          }}
        >
          {formatMessage({ id: 'page.tenants.new' })}
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
        title={formatMessage({ id: 'page.tenants.modalNewTitle' })}
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        destroyOnClose
        okText={formatMessage({ id: 'page.tenants.modalCreate' })}
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
            message.success(formatMessage({ id: 'page.tenants.created' }));
            notification.success({
              message: formatMessage({ id: 'page.tenants.notificationCreated' }),
              duration: 14,
              description: (
                <div>
                  <p style={{ marginBottom: 8 }}>{formatMessage({ id: 'page.tenants.createdNotifyP1' }, { name: created.name })}</p>
                  <p style={{ marginBottom: 8 }}>{formatMessage({ id: 'page.tenants.createdNotifyP2' })}</p>
                  <Typography.Text type="secondary">{formatMessage({ id: 'page.tenants.copyTenantId' })}</Typography.Text>
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
          <Form.Item name="name" label={formatMessage({ id: 'page.tenants.displayName' })} rules={[{ required: true, message: formatMessage({ id: 'page.tenants.displayNameRequired' }) }]}>
            <Input placeholder={formatMessage({ id: 'page.tenants.namePlaceholder' })} />
          </Form.Item>
          <Form.Item
            name="slug"
            label={formatMessage({ id: 'page.tenants.slugLabel' })}
            rules={[
              { required: true, message: formatMessage({ id: 'page.tenants.slugRequired' }) },
              { pattern: slugPattern, message: formatMessage({ id: 'page.tenants.slugPatternMsg' }) },
            ]}
            extra={formatMessage({ id: 'page.tenants.slugExtra' })}
          >
            <Input placeholder={formatMessage({ id: 'page.tenants.slugPlaceholder' })} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={row ? formatMessage({ id: 'page.tenants.editTitle' }, { slug: row.slug }) : ''}
        open={open}
        onCancel={() => setOpen(false)}
        okText={formatMessage({ id: 'page.tenants.editModalOk' })}
        width={720}
        onOk={async () => {
          if (!row) return;
          const v = await form.validateFields();
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
          message.success(formatMessage({ id: 'page.tenants.updated' }));
          setOpen(false);
          actionRef.current?.reload();
        }}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label={formatMessage({ id: 'page.tenants.editNameLabel' })} rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="require_encrypted_artifacts" label={formatMessage({ id: 'page.tenants.editRequireEnc' })} valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="require_mfa_for_admins" label={formatMessage({ id: 'page.tenants.requireMfaLabel' })} valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="kms_envelope_key_id" label={formatMessage({ id: 'page.tenants.editKms' })}>
            <Input placeholder={formatMessage({ id: 'page.tenants.placeholderClear' })} />
          </Form.Item>
          <Form.Item name="s3_bucket" label={formatMessage({ id: 'page.tenants.editS3Bucket' })}>
            <Input placeholder={formatMessage({ id: 'page.tenants.placeholderClear' })} />
          </Form.Item>
          <Form.Item name="s3_assume_role_arn" label={formatMessage({ id: 'page.tenants.editRoleArn' })}>
            <Input placeholder={formatMessage({ id: 'page.tenants.placeholderClear' })} />
          </Form.Item>
          <Form.Item name="s3_assume_role_external_id" label={formatMessage({ id: 'page.tenants.editExternalId' })}>
            <Input placeholder={formatMessage({ id: 'page.tenants.placeholderClear' })} />
          </Form.Item>
          <Form.Item name="policy_paths_allowlist_mode" label={formatMessage({ id: 'page.tenants.editAllowlist' })}>
            <Select
              options={[
                { value: 'off', label: 'off' },
                { value: 'warn', label: 'warn' },
                { value: 'enforce', label: 'enforce' },
              ]}
            />
          </Form.Item>
          <Typography.Title level={5} style={{ marginTop: 16 }}>
            {formatMessage({ id: 'page.tenants.ssoSection' })}
          </Typography.Title>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 8 }}>
            {formatMessage({ id: 'page.tenants.ssoIntro' })}
          </Typography.Paragraph>
          <Form.Item name="sso_oidc_issuer" label={formatMessage({ id: 'page.tenants.ssoIssuerField' })}>
            <Input placeholder={formatMessage({ id: 'page.tenants.clearOidc' })} />
          </Form.Item>
          <Form.Item name="sso_oidc_audience" label={formatMessage({ id: 'page.tenants.ssoAudienceField' })}>
            <Input placeholder={formatMessage({ id: 'page.tenants.pairWithIssuer' })} />
          </Form.Item>
          <Form.Item name="sso_oidc_role_claim" label={formatMessage({ id: 'page.tenants.ssoRoleClaim' })}>
            <Input />
          </Form.Item>
          <Form.Item name="sso_oidc_email_claim" label={formatMessage({ id: 'page.tenants.oidcEmailClaim' })}>
            <Input />
          </Form.Item>
          <Form.Item name="sso_jit_provisioning" label={formatMessage({ id: 'page.tenants.jitLabel' })} valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="sso_password_login_disabled" label={formatMessage({ id: 'page.tenants.passwordDisabledLabel' })} valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="sso_saml_entity_id" label={formatMessage({ id: 'page.tenants.samlEntity' })}>
            <Input placeholder={formatMessage({ id: 'page.tenants.optional' })} />
          </Form.Item>
          <Form.Item name="sso_saml_acs_url" label={formatMessage({ id: 'page.tenants.samlAcs' })}>
            <Input placeholder={formatMessage({ id: 'page.tenants.optional' })} />
          </Form.Item>
        </Form>
      </Modal>
    </PageContainer>
  );
};

export default TenantsAdminPage;
