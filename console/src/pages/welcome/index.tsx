import { LinkOutlined, RocketOutlined } from '@ant-design/icons';
import { PageContainer, ProCard } from '@ant-design/pro-components';
import { history, Link } from '@umijs/max';
import { Button, Col, Row, Statistic, Typography } from 'antd';
import React from 'react';

/**
 * 欢迎页：版式参考 Ant Design Pro Welcome（精简：无装饰底图与复杂图表）。
 */
const Welcome: React.FC = () => (
  <PageContainer title="欢迎">
    <ProCard
      style={{ marginBottom: 16 }}
      bordered
      extra={
        <Button type="primary" icon={<RocketOutlined />} onClick={() => history.push('/overview/workbench')}>
          进入工作台
        </Button>
      }
    >
      <Typography.Paragraph>
        使用左侧导航进入各业务分区；当前租户由顶栏选择器控制，请求自动携带{' '}
        <Typography.Text code>X-DeVault-Tenant-Id</Typography.Text>。
      </Typography.Paragraph>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={8}>
          <ProCard bordered>
            <Statistic title="控制台" value="DeVault" prefix={<LinkOutlined />} />
            <Typography.Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 0 }}>
              企业控制台基于 Umi 4 + Ant Design Pro 布局模板。
            </Typography.Paragraph>
          </ProCard>
        </Col>
        <Col xs={24} sm={12} md={8}>
          <ProCard bordered>
            <Statistic title="文档" value="OpenAPI" />
            <Typography.Link href="/docs" target="_blank" rel="noreferrer">
              打开 /docs
            </Typography.Link>
          </ProCard>
        </Col>
        <Col xs={24} sm={12} md={8}>
          <ProCard bordered>
            <Statistic title="下一步" value="作业中心" />
            <Link to="/overview/workbench">查看工作台</Link>
          </ProCard>
        </Col>
      </Row>
    </ProCard>
  </PageContainer>
);

export default Welcome;
