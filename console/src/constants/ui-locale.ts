/** 与 Umi `umi_locale` 同步写入，便于运维检索与文档对齐；实际读取以 `getLocale()` 为准。 */
export const STORAGE_UI_LOCALE_KEY = 'devault_ui_locale';

export type UiLocaleId = 'en-US' | 'zh-CN';

export const UI_LOCALES: { id: UiLocaleId; labelKey: string }[] = [
  { id: 'en-US', labelKey: 'lang.en' },
  { id: 'zh-CN', labelKey: 'lang.zh' },
];
