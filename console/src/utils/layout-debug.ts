import type { MenuDataItem } from '@ant-design/pro-layout';

import { isDevaultAuthDebugEnabled } from '@/utils/auth-debug';

const PREFIX = '[devault:layout]';

function runtimeLayoutFlagOn(): boolean {
  if (typeof globalThis === 'undefined') return false;
  try {
    return (globalThis as unknown as { __DEVAULT_LAYOUT_DEBUG__?: boolean }).__DEVAULT_LAYOUT_DEBUG__ === true;
  } catch {
    return false;
  }
}

function localStorageLayoutOn(): boolean {
  if (typeof window === 'undefined') return false;
  try {
    return window.localStorage?.getItem('devault_console_layout_debug') === '1';
  } catch {
    return false;
  }
}

/** 开发 / auth 调试 / 或显式打开布局专用开关时输出 `[devault:layout]` 日志。 */
export function isLayoutDebugEnabled(): boolean {
  return isDevaultAuthDebugEnabled() || runtimeLayoutFlagOn() || localStorageLayoutOn();
}

export function layoutDebug(message: string, payload?: Record<string, unknown>): void {
  if (!isLayoutDebugEnabled()) return;
  if (payload !== undefined) {
    console.log(PREFIX, message, payload);
  } else {
    console.log(PREFIX, message);
  }
}

/** 仅统计与路径预览，避免整棵 route 对象刷屏。 */
export function summarizeMenuData(menuData: MenuDataItem[], maxDepth = 4, depth = 0): unknown[] {
  if (depth > maxDepth) return ['…'];
  return menuData.map((item) => {
    const kids = item.children ?? item.routes;
    const childArr = Array.isArray(kids) ? kids : undefined;
    return {
      path: item.path,
      name: item.name,
      hideInMenu: item.hideInMenu,
      access: item.access,
      unaccessible: item.unaccessible,
      childrenCount: childArr?.length ?? 0,
      children:
        childArr && childArr.length > 0 ? summarizeMenuData(childArr as MenuDataItem[], maxDepth, depth + 1) : undefined,
    };
  });
}

let layoutProbeOnce = false;

/** 首次进入 layout 时打一条探针，确认打包与开关。 */
export function layoutDebugBootProbe(extra?: Record<string, unknown>): void {
  if (!isLayoutDebugEnabled() || layoutProbeOnce) return;
  layoutProbeOnce = true;
  if (typeof window !== 'undefined') {
    console.log(PREFIX, 'boot:layoutProbe', {
      NODE_ENV: process.env.NODE_ENV,
      pathname: window.location.pathname,
      ...extra,
    });
  }
}
