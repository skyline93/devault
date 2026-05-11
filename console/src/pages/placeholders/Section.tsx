import { PageContainer, ProCard } from '@ant-design/pro-components';
import { useIntl, useLocation } from '@umijs/max';
import { Typography } from 'antd';
import React, { useMemo } from 'react';

const GROUP: Record<string, string> = {
  '/backup': 'backup',
  '/execution': 'execution',
  '/compliance': 'compliance',
  '/platform': 'platform',
};

const Section: React.FC = () => {
  const { formatMessage } = useIntl();
  const { pathname } = useLocation();
  const titleKey = useMemo(() => {
    const k = GROUP[pathname];
    return k ? `page.placeholder.${k}` : 'page.placeholder.generic';
  }, [pathname]);

  return (
    <PageContainer title={formatMessage({ id: titleKey })}>
      <ProCard>
        <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
          {formatMessage({ id: 'page.placeholder.body' })}
        </Typography.Paragraph>
      </ProCard>
    </PageContainer>
  );
};

export default Section;
