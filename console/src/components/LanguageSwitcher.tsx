import { Select } from 'antd';
import React, { useMemo } from 'react';
import { getLocale, setLocale, useIntl } from '@umijs/max';

import { STORAGE_UI_LOCALE_KEY, UI_LOCALES, type UiLocaleId } from '@/constants/ui-locale';

const isUiLocale = (v: string): v is UiLocaleId => v === 'en-US' || v === 'zh-CN';

/**
 * 顶栏语言切换：与 Umi locale 插件、`umi_locale` 及 `devault_ui_locale` 对齐。
 */
const LanguageSwitcher: React.FC = () => {
  const { formatMessage } = useIntl();
  const current = getLocale();

  const options = useMemo(
    () =>
      UI_LOCALES.map((l) => ({
        value: l.id,
        label: formatMessage({ id: l.labelKey }),
      })),
    [formatMessage],
  );

  return (
    <Select
      size="small"
      variant="borderless"
      style={{ minWidth: 128 }}
      value={isUiLocale(current) ? current : 'en-US'}
      options={options}
      onChange={(lang: UiLocaleId) => {
        try {
          localStorage.setItem(STORAGE_UI_LOCALE_KEY, lang);
        } catch {
          /* ignore */
        }
        setLocale(lang, true);
      }}
      aria-label={formatMessage({ id: 'component.language' })}
    />
  );
};

export default LanguageSwitcher;
