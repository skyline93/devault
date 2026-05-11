import { useIntl } from '@umijs/max';
import React, { useLayoutEffect } from 'react';

/**
 * 同步 `document.documentElement.lang`，满足可访问性与浏览器语义。
 */
const DocumentLang: React.FC = () => {
  const { locale } = useIntl();
  useLayoutEffect(() => {
    document.documentElement.lang = locale.startsWith('zh') ? 'zh-CN' : 'en';
  }, [locale]);
  return null;
};

export default DocumentLang;
