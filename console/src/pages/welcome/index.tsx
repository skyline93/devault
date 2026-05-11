import { LinkOutlined, RocketOutlined } from '@ant-design/icons';
import { PageContainer, ProCard } from '@ant-design/pro-components';
import { history, Link, useIntl } from '@umijs/max';
import { Button, Col, Row, Statistic, Typography } from 'antd';
import React from 'react';

const Welcome: React.FC = () => {
  const { formatMessage } = useIntl();
  return (
    <PageContainer title={formatMessage({ id: 'page.welcome.title' })}>
      <ProCard
        style={{ marginBottom: 16 }}
        bordered
        extra={
          <Button type="primary" icon={<RocketOutlined />} onClick={() => history.push('/overview/workbench')}>
            {formatMessage({ id: 'page.welcome.enterWorkbench' })}
          </Button>
        }
      >
        <Typography.Paragraph>{formatMessage({ id: 'page.welcome.intro' })}</Typography.Paragraph>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} md={8}>
            <ProCard bordered>
              <Statistic title={formatMessage({ id: 'page.welcome.cardConsoleTitle' })} value="DeVault" prefix={<LinkOutlined />} />
              <Typography.Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 0 }}>
                {formatMessage({ id: 'page.welcome.cardConsoleDesc' })}
              </Typography.Paragraph>
            </ProCard>
          </Col>
          <Col xs={24} sm={12} md={8}>
            <ProCard bordered>
              <Statistic title={formatMessage({ id: 'page.welcome.cardDocsTitle' })} value="OpenAPI" />
              <Typography.Link href="/docs" target="_blank" rel="noreferrer">
                {formatMessage({ id: 'page.welcome.cardDocsLink' })}
              </Typography.Link>
            </ProCard>
          </Col>
          <Col xs={24} sm={12} md={8}>
            <ProCard bordered>
              <Statistic title={formatMessage({ id: 'page.welcome.cardNextTitle' })} value={formatMessage({ id: 'page.welcome.cardNextValue' })} />
              <Link to="/overview/workbench">{formatMessage({ id: 'page.welcome.cardNextLink' })}</Link>
            </ProCard>
          </Col>
        </Row>
      </ProCard>
    </PageContainer>
  );
};

export default Welcome;
