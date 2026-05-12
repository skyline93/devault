import { PageContainer } from '@ant-design/pro-components';
import { history, request, useIntl, useParams } from '@umijs/max';
import { Card } from 'antd';
import React, { useCallback, useEffect, useState } from 'react';

const FleetAgentDetailPage: React.FC = () => {
  const { formatMessage } = useIntl();
  const { agentId } = useParams<{ agentId: string }>();
  const [agent, setAgent] = useState<API.EdgeAgentOut | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!agentId) return;
    setLoading(true);
    try {
      const a = await request<API.EdgeAgentOut>(`/api/v1/agents/${agentId}`);
      setAgent(a);
    } finally {
      setLoading(false);
    }
  }, [agentId]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!agentId) return null;

  return (
    <PageContainer
      title={formatMessage({ id: 'page.fleetDetail.pageTitle' }, { agentId })}
      loading={loading}
      onBack={() => history.push('/execution/fleet')}
    >
      {agent ? (
        <Card title={formatMessage({ id: 'page.fleetDetail.snapshot' })}>
          <pre style={{ fontSize: 12, background: '#f5f5f5', padding: 12, borderRadius: 8, overflow: 'auto' }}>
            {JSON.stringify(agent, null, 2)}
          </pre>
        </Card>
      ) : null}
    </PageContainer>
  );
};

export default FleetAgentDetailPage;
