import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { request, useIntl } from '@umijs/max';
import { App, Button, Drawer, Form, Input, Select, Space, Switch } from 'antd';
import React, { useCallback, useMemo, useRef, useState } from 'react';

import { detailFromError } from '@/requestErrorConfig';

const slugPattern = /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/;

type StorageProfileRow = {
  id: string;
  name: string;
  slug: string;
  storage_type: string;
  is_active: boolean;
  local_root?: string | null;
  s3_endpoint?: string | null;
  s3_region?: string | null;
  s3_bucket?: string | null;
  s3_assume_role_arn?: string | null;
  s3_assume_role_external_id?: string | null;
  has_static_credentials: boolean;
};

const PlatformStoragePage: React.FC = () => {
  const { formatMessage } = useIntl();
  const { message } = App.useApp();
  const actionRef = useRef<ActionType>();
  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [row, setRow] = useState<StorageProfileRow | null>(null);
  const [createForm] = Form.useForm();
  const [editForm] = Form.useForm();
  const createStorageType = Form.useWatch('storage_type', createForm);
  const editStorageType = Form.useWatch('storage_type', editForm);

  const columns: ProColumns<StorageProfileRow>[] = useMemo(
    () => [
      { title: formatMessage({ id: 'page.storage.colType' }), dataIndex: 'storage_type', width: 90 },
      {
        title: formatMessage({ id: 'page.storage.colActive' }),
        dataIndex: 'is_active',
        width: 90,
        render: (_, r) => (r.is_active ? formatMessage({ id: 'page.tenants.yes' }) : formatMessage({ id: 'page.tenants.no' })),
      },
      {
        title: formatMessage({ id: 'page.storage.colConnection' }),
        dataIndex: 's3_endpoint',
        ellipsis: true,
        render: (_, r) => {
          if (r.storage_type === 'local') {
            return r.local_root ?? '—';
          }
          return r.s3_endpoint ?? '—';
        },
      },
      {
        title: formatMessage({ id: 'page.storage.colBucket' }),
        dataIndex: 's3_bucket',
        width: 200,
        ellipsis: true,
        render: (_, r) => (r.storage_type === 's3' ? r.s3_bucket ?? '—' : '—'),
      },
      {
        title: formatMessage({ id: 'page.storage.colRegion' }),
        dataIndex: 's3_region',
        width: 140,
        ellipsis: true,
        render: (_, r) => (r.storage_type === 's3' ? r.s3_region ?? formatMessage({ id: 'page.storage.regionDefault' }) : '—'),
      },
      {
        title: formatMessage({ id: 'page.storage.colCreds' }),
        dataIndex: 'has_static_credentials',
        width: 120,
        render: (_, r) =>
          r.has_static_credentials ? formatMessage({ id: 'page.storage.credsYes' }) : formatMessage({ id: 'page.storage.credsNo' }),
      },
      {
        title: formatMessage({ id: 'page.tenants.colActions' }),
        valueType: 'option',
        width: 260,
        render: (_, r) => (
          <Space>
            <Button
              type="link"
              size="small"
              onClick={() => {
                setRow(r);
                editForm.setFieldsValue({
                  name: r.name,
                  storage_type: r.storage_type,
                  local_root: r.local_root ?? '',
                  s3_endpoint: r.s3_endpoint ?? '',
                  s3_region: r.s3_region ?? '',
                  s3_bucket: r.s3_bucket ?? '',
                  s3_assume_role_arn: r.s3_assume_role_arn ?? '',
                  s3_assume_role_external_id: r.s3_assume_role_external_id ?? '',
                  s3_access_key: '',
                  s3_secret_key: '',
                });
                setEditOpen(true);
              }}
            >
              {formatMessage({ id: 'page.storage.edit' })}
            </Button>
            {!r.is_active ? (
              <Button
                type="link"
                size="small"
                onClick={async () => {
                  try {
                    await request(`/api/v1/storage-profiles/${r.id}/activate`, { method: 'POST' });
                    message.success(formatMessage({ id: 'page.storage.activated' }));
                    actionRef.current?.reload();
                  } catch (e) {
                    message.error(detailFromError(e));
                  }
                }}
              >
                {formatMessage({ id: 'page.storage.activate' })}
              </Button>
            ) : null}
            <Button
              type="link"
              danger
              size="small"
              disabled={r.is_active}
              onClick={async () => {
                try {
                  await request(`/api/v1/storage-profiles/${r.id}`, { method: 'DELETE' });
                  message.success(formatMessage({ id: 'page.storage.deleted' }));
                  actionRef.current?.reload();
                } catch (e) {
                  message.error(detailFromError(e));
                }
              }}
            >
              {formatMessage({ id: 'page.storage.delete' })}
            </Button>
          </Space>
        ),
      },
    ],
    [actionRef, editForm, formatMessage, message],
  );

  const submitCreate = useCallback(async () => {
    const v = await createForm.validateFields();
    const body: Record<string, unknown> = {
      storage_type: v.storage_type,
      is_active: Boolean(v.is_active),
    };
    if (v.storage_type === 'local') {
      body.name = String(v.name ?? '').trim();
      body.slug = String(v.slug ?? '')
        .trim()
        .toLowerCase();
      body.local_root = String(v.local_root ?? '').trim();
    } else {
      body.s3_endpoint = String(v.s3_endpoint ?? '').trim();
      const reg = String(v.s3_region ?? '').trim();
      if (reg) body.s3_region = reg;
      body.s3_bucket = String(v.s3_bucket ?? '').trim();
      body.s3_access_key = String(v.s3_access_key ?? '').trim();
      body.s3_secret_key = String(v.s3_secret_key ?? '').trim();
      const arn = String(v.s3_assume_role_arn ?? '').trim();
      const ext = String(v.s3_assume_role_external_id ?? '').trim();
      if (arn) body.s3_assume_role_arn = arn;
      if (ext) body.s3_assume_role_external_id = ext;
    }
    try {
      await request('/api/v1/storage-profiles', { method: 'POST', data: body, skipErrorHandler: true });
      message.success(formatMessage({ id: 'page.storage.created' }));
      setCreateOpen(false);
      actionRef.current?.reload();
    } catch (e) {
      message.error(detailFromError(e));
      throw e;
    }
  }, [createForm, formatMessage, message]);

  const submitEdit = useCallback(async () => {
    if (!row) return;
    const v = await editForm.validateFields();
    const body: Record<string, unknown> = {};
    if (row.storage_type === 'local') {
      body.name = String(v.name ?? '').trim();
      body.local_root = String(v.local_root ?? '').trim();
    }
    if (row.storage_type === 's3') {
      body.s3_endpoint = String(v.s3_endpoint ?? '').trim();
      const reg = String(v.s3_region ?? '').trim();
      body.s3_region = reg.length ? reg : '';
      body.s3_bucket = String(v.s3_bucket ?? '').trim();
      const arn = String(v.s3_assume_role_arn ?? '').trim();
      const ext = String(v.s3_assume_role_external_id ?? '').trim();
      body.s3_assume_role_arn = arn.length ? arn : '';
      body.s3_assume_role_external_id = ext.length ? ext : '';
      const ak = String(v.s3_access_key ?? '').trim();
      const sk = String(v.s3_secret_key ?? '').trim();
      if (ak || sk) {
        if (!ak || !sk) {
          message.error(formatMessage({ id: 'page.storage.credsPairEdit' }));
          return;
        }
        body.s3_access_key = ak;
        body.s3_secret_key = sk;
      }
    }
    try {
      await request(`/api/v1/storage-profiles/${row.id}`, { method: 'PATCH', data: body, skipErrorHandler: true });
      message.success(formatMessage({ id: 'page.storage.updated' }));
      setEditOpen(false);
      actionRef.current?.reload();
    } catch (e) {
      message.error(detailFromError(e));
      throw e;
    }
  }, [editForm, formatMessage, message, row]);

  return (
    <PageContainer title={formatMessage({ id: 'page.storage.title' })} subTitle={formatMessage({ id: 'page.storage.subtitle' })}>
      <div style={{ marginBottom: 16 }}>
        <Button
          type="primary"
          onClick={() => {
            createForm.resetFields();
            createForm.setFieldsValue({
              storage_type: 's3',
              is_active: false,
            });
            setCreateOpen(true);
          }}
        >
          {formatMessage({ id: 'page.storage.new' })}
        </Button>
      </div>

      <ProTable<StorageProfileRow>
        rowKey="id"
        actionRef={actionRef}
        columns={columns}
        search={false}
        request={async () => {
          const data = await request<StorageProfileRow[]>('/api/v1/storage-profiles');
          return { data, success: true, total: data.length };
        }}
        pagination={{ pageSize: 20 }}
      />

      <Drawer
        title={formatMessage({ id: 'page.storage.drawerCreateTitle' })}
        placement="right"
        width={560}
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        destroyOnClose
        footer={
          <div style={{ textAlign: 'right' }}>
            <Space>
              <Button onClick={() => setCreateOpen(false)}>{formatMessage({ id: 'page.storage.drawerCancel' })}</Button>
              <Button type="primary" onClick={submitCreate}>
                {formatMessage({ id: 'page.storage.drawerCreateOk' })}
              </Button>
            </Space>
          </div>
        }
      >
        <Form form={createForm} layout="vertical">
          <Form.Item name="storage_type" label={formatMessage({ id: 'page.storage.fieldType' })} rules={[{ required: true }]}>
            <Select
              options={[
                { value: 's3', label: 'S3' },
                { value: 'local', label: 'Local' },
              ]}
            />
          </Form.Item>
          <Form.Item name="is_active" label={formatMessage({ id: 'page.storage.fieldActivateOnCreate' })} valuePropName="checked">
            <Switch />
          </Form.Item>
          {createStorageType === 'local' ? (
            <>
              <Form.Item name="name" label={formatMessage({ id: 'page.storage.fieldName' })} rules={[{ required: true }]}>
                <Input />
              </Form.Item>
              <Form.Item
                name="slug"
                label={formatMessage({ id: 'page.storage.fieldSlug' })}
                rules={[
                  { required: true },
                  { pattern: slugPattern, message: formatMessage({ id: 'page.storage.slugPattern' }) },
                ]}
                extra={formatMessage({ id: 'page.storage.slugExtra' })}
              >
                <Input />
              </Form.Item>
              <Form.Item name="local_root" label={formatMessage({ id: 'page.storage.fieldLocalRoot' })} rules={[{ required: true }]}>
                <Input placeholder="./data/storage" />
              </Form.Item>
            </>
          ) : null}
          {createStorageType === 's3' ? (
            <>
              <Form.Item name="s3_endpoint" label={formatMessage({ id: 'page.storage.fieldS3Endpoint' })} rules={[{ required: true }]}>
                <Input placeholder="https://s3.amazonaws.com" />
              </Form.Item>
              <Form.Item name="s3_bucket" label={formatMessage({ id: 'page.storage.fieldS3Bucket' })} rules={[{ required: true }]}>
                <Input />
              </Form.Item>
              <Form.Item name="s3_region" label={formatMessage({ id: 'page.storage.fieldS3RegionOptional' })}>
                <Input placeholder={formatMessage({ id: 'page.storage.regionPlaceholder' })} />
              </Form.Item>
              <Form.Item
                name="s3_access_key"
                label={formatMessage({ id: 'page.storage.fieldS3AccessKey' })}
                rules={[{ required: true }]}
              >
                <Input.Password autoComplete="new-password" />
              </Form.Item>
              <Form.Item
                name="s3_secret_key"
                label={formatMessage({ id: 'page.storage.fieldS3SecretKey' })}
                rules={[{ required: true }]}
              >
                <Input.Password autoComplete="new-password" />
              </Form.Item>
              <Form.Item name="s3_assume_role_arn" label={formatMessage({ id: 'page.storage.fieldAssumeRoleArn' })}>
                <Input />
              </Form.Item>
              <Form.Item name="s3_assume_role_external_id" label={formatMessage({ id: 'page.storage.fieldAssumeRoleExt' })}>
                <Input />
              </Form.Item>
            </>
          ) : null}
        </Form>
      </Drawer>

      <Drawer
        title={
          row
            ? row.storage_type === 's3'
              ? formatMessage({ id: 'page.storage.drawerEditTitleS3' }, { bucket: row.s3_bucket ?? row.slug })
              : formatMessage({ id: 'page.storage.drawerEditTitleLocal' }, { slug: row.slug })
            : ''
        }
        placement="right"
        width={560}
        open={editOpen}
        onClose={() => setEditOpen(false)}
        destroyOnClose
        footer={
          <div style={{ textAlign: 'right' }}>
            <Space>
              <Button onClick={() => setEditOpen(false)}>{formatMessage({ id: 'page.storage.drawerCancel' })}</Button>
              <Button type="primary" onClick={submitEdit}>
                {formatMessage({ id: 'page.storage.drawerEditOk' })}
              </Button>
            </Space>
          </div>
        }
      >
        <Form form={editForm} layout="vertical">
          <Form.Item name="storage_type" hidden>
            <Input />
          </Form.Item>
          {editStorageType === 'local' ? (
            <>
              <Form.Item label={formatMessage({ id: 'page.storage.fieldSlug' })}>
                <Input disabled value={row?.slug} />
              </Form.Item>
              <Form.Item name="name" label={formatMessage({ id: 'page.storage.fieldName' })} rules={[{ required: true }]}>
                <Input />
              </Form.Item>
              <Form.Item name="local_root" label={formatMessage({ id: 'page.storage.fieldLocalRoot' })} rules={[{ required: true }]}>
                <Input />
              </Form.Item>
            </>
          ) : null}
          {editStorageType === 's3' ? (
            <>
              <Form.Item name="s3_endpoint" label={formatMessage({ id: 'page.storage.fieldS3Endpoint' })} rules={[{ required: true }]}>
                <Input />
              </Form.Item>
              <Form.Item name="s3_bucket" label={formatMessage({ id: 'page.storage.fieldS3Bucket' })} rules={[{ required: true }]}>
                <Input />
              </Form.Item>
              <Form.Item name="s3_region" label={formatMessage({ id: 'page.storage.fieldS3RegionOptional' })}>
                <Input placeholder={formatMessage({ id: 'page.storage.regionPlaceholder' })} />
              </Form.Item>
              <Form.Item name="s3_access_key" label={formatMessage({ id: 'page.storage.fieldS3AccessKey' })}>
                <Input.Password autoComplete="new-password" placeholder={formatMessage({ id: 'page.storage.leaveBlankCreds' })} />
              </Form.Item>
              <Form.Item name="s3_secret_key" label={formatMessage({ id: 'page.storage.fieldS3SecretKey' })}>
                <Input.Password autoComplete="new-password" placeholder={formatMessage({ id: 'page.storage.leaveBlankCreds' })} />
              </Form.Item>
              <Form.Item name="s3_assume_role_arn" label={formatMessage({ id: 'page.storage.fieldAssumeRoleArn' })}>
                <Input />
              </Form.Item>
              <Form.Item name="s3_assume_role_external_id" label={formatMessage({ id: 'page.storage.fieldAssumeRoleExt' })}>
                <Input />
              </Form.Item>
            </>
          ) : null}
        </Form>
      </Drawer>
    </PageContainer>
  );
};

export default PlatformStoragePage;
