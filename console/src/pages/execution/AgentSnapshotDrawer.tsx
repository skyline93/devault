import { request, useIntl } from '@umijs/max';
import { App, Card, Drawer, Spin } from 'antd';
import React, { useEffect, useState } from 'react';

export type AgentSnapshotDrawerProps = {
  open: boolean;
  agentId: string | undefined;
  onClose: () => void;
};

const AgentSnapshotDrawer: React.FC<AgentSnapshotDrawerProps> = ({ open, agentId, onClose }) => {
  const { formatMessage } = useIntl();
  const { message } = App.useApp();
  const [agent, setAgent] = useState<API.EdgeAgentOut | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open || !agentId) {
      setAgent(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    void request<API.EdgeAgentOut>(`/api/v1/agents/${agentId}`)
      .then((a) => {
        if (!cancelled) setAgent(a);
      })
      .catch(() => {
        if (!cancelled) message.error(formatMessage({ id: 'page.agentSnapshot.loadFailed' }));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, agentId, formatMessage, message]);

  return (
    <Drawer open={open} onClose={onClose} width={640} destroyOnClose title={formatMessage({ id: 'page.agentSnapshot.drawerTitle' })}>
      <Spin spinning={loading}>
        {agent ? (
          <Card title={formatMessage({ id: 'page.fleetDetail.snapshot' })}>
            <pre style={{ fontSize: 12, background: 'var(--ant-color-fill-alter)', padding: 12, borderRadius: 8, overflow: 'auto' }}>
              {JSON.stringify(agent, null, 2)}
            </pre>
          </Card>
        ) : null}
      </Spin>
    </Drawer>
  );
};

export default AgentSnapshotDrawer;
