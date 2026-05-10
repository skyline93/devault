import { PageContainer, ProCard } from '@ant-design/pro-components';
import { useLocation } from '@umijs/max';
import { Typography } from 'antd';
import React from 'react';

const TITLES: Record<string, string> = {
  '/backup': '备份与恢复',
  '/execution': '执行面',
  '/compliance': '合规与演练',
  '/platform': '平台管理',
};

/**
 * 侧栏五大分组中尚未落地的分区占位（十五-09 壳 + 十五-11 起迭代）。
 */
const Section: React.FC = () => {
  const { pathname } = useLocation();
  const title = TITLES[pathname] ?? '子模块';

  return (
    <PageContainer title={title}>
      <ProCard>
        <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
          该分区具体页面将在后续 backlog（十五-11 起）中按 REST 竖切交付。当前路由用于信息架构与导航验收。
        </Typography.Paragraph>
      </ProCard>
    </PageContainer>
  );
};

export default Section;
