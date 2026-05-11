import { STORAGE_UI_LOCALE_KEY } from './constants/ui-locale';

/** 在 Umi locale 插件读 `umi_locale` 之前对齐历史键（仅当存在 devault 键且 umi 键为空）。 */
if (typeof window !== 'undefined') {
  try {
    const preferred = window.localStorage.getItem(STORAGE_UI_LOCALE_KEY);
    const umi = window.localStorage.getItem('umi_locale');
    if (preferred && !umi) {
      window.localStorage.setItem('umi_locale', preferred);
    }
  } catch {
    /* ignore */
  }
}
