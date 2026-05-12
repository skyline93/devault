import { agentPrimaryLabel } from '../../execution/agentDisplay';
import { useIntl } from '@umijs/max';
import { Card, Col, Form, Input, InputNumber, Row, Select, Space, Switch } from 'antd';
import React from 'react';

export type PolicyFormFieldsProps = {
  tenantAgents: API.TenantScopedAgentOut[];
  pathsAgentDisabled: boolean;
};

const PolicyFormFields: React.FC<PolicyFormFieldsProps> = ({ tenantAgents, pathsAgentDisabled }) => {
  const { formatMessage } = useIntl();

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      <Card size="small" title={formatMessage({ id: 'page.policyEdit.sectionNameAndBinding' })}>
        <Row gutter={[16, 16]}>
          <Col xs={24} md={12}>
            <Form.Item
              name="name"
              label={formatMessage({ id: 'page.policyEdit.name' })}
              rules={[{ required: true, message: formatMessage({ id: 'page.policyEdit.nameRequired' }) }]}
            >
              <Input maxLength={255} />
            </Form.Item>
          </Col>
          <Col xs={24} md={12}>
            {pathsAgentDisabled ? (
              <div style={{ marginBottom: 8, color: 'var(--ant-color-text-secondary)', fontSize: 12 }}>
                {formatMessage({ id: 'page.policyEdit.pathsAgentLockedHint' })}
              </div>
            ) : null}
            <Form.Item
              name="bound_agent_id"
              label={formatMessage({ id: 'page.policyEdit.agentHostLabel' })}
              rules={
                pathsAgentDisabled
                  ? []
                  : [{ required: true, message: formatMessage({ id: 'page.policyEdit.agentHostRequired' }) }]
              }
            >
              <Select
                showSearch
                disabled={pathsAgentDisabled}
                optionFilterProp="label"
                options={tenantAgents.map((a) => ({
                  value: a.id,
                  label: agentPrimaryLabel(a.hostname, formatMessage({ id: 'page.policies.agentHostnameUnknown' })),
                }))}
              />
            </Form.Item>
          </Col>
        </Row>
      </Card>

      <Card size="small" title={formatMessage({ id: 'page.policyEdit.sectionFileBackup' })}>
        <Form.Item
          name="pathsText"
          label={formatMessage({ id: 'page.policyEdit.pathsLabel' })}
          rules={[{ required: true, message: formatMessage({ id: 'page.policyEdit.pathsRequired' }) }]}
        >
          <Input.TextArea
            rows={4}
            readOnly={pathsAgentDisabled}
            style={pathsAgentDisabled ? { background: 'var(--ant-color-fill-alter)', cursor: 'not-allowed' } : undefined}
            placeholder={formatMessage({ id: 'page.policyEdit.pathsPlaceholder' })}
          />
        </Form.Item>
        <Form.Item name="excludesText" label={formatMessage({ id: 'page.policyEdit.excludesLabel' })}>
          <Input.TextArea rows={3} placeholder={formatMessage({ id: 'page.policyEdit.excludesPlaceholder' })} />
        </Form.Item>
        <Row gutter={[16, 8]}>
          <Col xs={24} sm={12} lg={8}>
            <Form.Item name="follow_symlinks" label={formatMessage({ id: 'page.policyEdit.followSymlinks' })} valuePropName="checked">
              <Switch />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12} lg={8}>
            <Form.Item name="preserve_uid_gid" label={formatMessage({ id: 'page.policyEdit.preserveUidGid' })} valuePropName="checked">
              <Switch defaultChecked />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12} lg={8}>
            <Form.Item name="one_filesystem" label={formatMessage({ id: 'page.policyEdit.oneFilesystem' })} valuePropName="checked">
              <Switch />
            </Form.Item>
          </Col>
        </Row>
        <Row gutter={[16, 8]}>
          <Col xs={24} md={12}>
            <Form.Item name="encrypt_artifacts" label={formatMessage({ id: 'page.policyEdit.encryptArtifacts' })} valuePropName="checked">
              <Switch />
            </Form.Item>
          </Col>
          <Col xs={24} md={12}>
            <Form.Item name="kms_envelope_key_id" label={formatMessage({ id: 'page.policyEdit.kmsLabel' })}>
              <Input placeholder={formatMessage({ id: 'page.policyEdit.kmsPh' })} />
            </Form.Item>
          </Col>
        </Row>
        <Row gutter={[16, 8]}>
          <Col xs={24} md={12}>
            <Form.Item name="object_lock_mode" label={formatMessage({ id: 'page.policyEdit.retentionMode' })}>
              <Select
                allowClear
                options={[
                  { value: 'GOVERNANCE', label: formatMessage({ id: 'page.policyEdit.objectLockGovernance' }) },
                  { value: 'COMPLIANCE', label: formatMessage({ id: 'page.policyEdit.objectLockCompliance' }) },
                ]}
              />
            </Form.Item>
          </Col>
          <Col xs={24} md={12}>
            <Form.Item name="object_lock_retain_days" label={formatMessage({ id: 'page.policyEdit.objectLockRetainDays' })}>
              <InputNumber
                min={1}
                style={{ width: '100%' }}
                placeholder={formatMessage({ id: 'page.policyEdit.objectLockRetainPlaceholder' })}
              />
            </Form.Item>
          </Col>
        </Row>
        <Row gutter={[16, 8]}>
          <Col xs={24} md={12}>
            <Form.Item name="retention_days" label={formatMessage({ id: 'page.policyEdit.backupRetentionDays' })}>
              <InputNumber min={1} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
        </Row>
      </Card>
    </Space>
  );
};

export default PolicyFormFields;
