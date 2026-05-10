import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { request } from '@umijs/max';
import { App, Button, Form, Input, Modal, Select, Switch } from 'antd';
import React, { useRef, useState } from 'react';

const TenantsAdminPage: React.FC = () => {
  const { message } = App.useApp();
  const actionRef = useRef<ActionType>();
  const [open, setOpen] = useState(false);
  const [row, setRow] = useState<API.TenantOut | null>(null);
  const [form] = Form.useForm();

  const columns: ProColumns<API.TenantOut>[] = [
    { title: '名称', dataIndex: 'name' },
    { title: 'slug', dataIndex: 'slug', copyable: true },
    { title: '强制加密制品', dataIndex: 'require_encrypted_artifacts', width: 120, render: (_, r) => (r.require_encrypted_artifacts ? '是' : '否') },
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
              kms_envelope_key_id: r.kms_envelope_key_id ?? '',
              s3_bucket: r.s3_bucket ?? '',
              s3_assume_role_arn: r.s3_assume_role_arn ?? '',
              s3_assume_role_external_id: r.s3_assume_role_external_id ?? '',
              policy_paths_allowlist_mode: r.policy_paths_allowlist_mode,
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
    <PageContainer title="租户（管理员）">
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
        title={row ? `编辑租户 ${row.slug}` : ''}
        open={open}
        onCancel={() => setOpen(false)}
        okText="PATCH 保存"
        width={640}
        onOk={async () => {
          if (!row) return;
          const v = await form.validateFields();
          /** 空字符串可走服务端 strip→None 清空 BYOB/KMS 等可选字段。 */
          const body: Record<string, unknown> = {
            name: v.name,
            require_encrypted_artifacts: v.require_encrypted_artifacts,
            policy_paths_allowlist_mode: v.policy_paths_allowlist_mode,
          };
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
        </Form>
      </Modal>
    </PageContainer>
  );
};

export default TenantsAdminPage;
