import { history, useParams } from '@umijs/max';
import React, { useEffect } from 'react';

/** 将旧版「整页编辑」深链重定向到策略列表并打开右侧抽屉。 */
const EditRedirect: React.FC = () => {
  const { policyId } = useParams<{ policyId: string }>();

  useEffect(() => {
    if (policyId) {
      history.replace(`/backup/policies?edit=${encodeURIComponent(policyId)}`);
    } else {
      history.replace('/backup/policies');
    }
  }, [policyId]);

  return null;
};

export default EditRedirect;
