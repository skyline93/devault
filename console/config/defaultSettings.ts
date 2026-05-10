import type { ProLayoutProps } from '@ant-design/pro-components';

/**
 * 与 [Ant Design Pro](https://github.com/ant-design/ant-design-pro) `config/defaultSettings` 对齐的基线；
 * 「精简」：无外链装饰 logo、无 `bgLayoutImgList`、不启用 SettingDrawer（由 `app.tsx` 控制）。
 */
const Settings: ProLayoutProps & {
  pwa?: boolean;
  logo?: string | false;
} = {
  navTheme: 'light',
  colorPrimary: '#1890ff',
  layout: 'mix',
  contentWidth: 'Fluid',
  fixedHeader: false,
  fixSiderbar: true,
  colorWeak: false,
  title: 'DeVault',
  pwa: false,
  /** 精简：不加载 Ant Design 默认 SVG logo，避免外网依赖 */
  logo: false,
  iconfontUrl: '',
  token: {},
};

export default Settings;
