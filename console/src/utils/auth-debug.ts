const PREFIX = '[devault:auth]';

/** 与 `config/config.ts` 中 `umiAuthDebugInject` 一致，运行时为字面量 `'0'` | `'1'`。 */
const buildAuthDebugOn = process.env.UMI_APP_AUTH_DEBUG === '1';

function runtimeFlagOn(): boolean {
  if (typeof globalThis === 'undefined') return false;
  try {
    return (globalThis as unknown as { __DEVAULT_AUTH_DEBUG__?: boolean }).__DEVAULT_AUTH_DEBUG__ === true;
  } catch {
    return false;
  }
}

/** 供布局/菜单等其它模块复用：与 `authDebug` 是否输出一致。 */
export function isDevaultAuthDebugEnabled(): boolean {
  if (runtimeFlagOn()) return true;
  if (buildAuthDebugOn) return true;
  if (process.env.NODE_ENV === 'development') return true;
  if (typeof window === 'undefined') return false;
  try {
    return window.localStorage?.getItem('devault_console_auth_debug') === '1';
  } catch {
    return false;
  }
}

function debugEnabled(): boolean {
  return isDevaultAuthDebugEnabled();
}

/**
 * 认证与会话排查日志，前缀 `[devault:auth]`，使用 **console.log**。
 *
 * - **默认开启**：生产构建未显式 `UMI_APP_AUTH_DEBUG=0` 时打入 `'1'`。
 * - **关闭**：构建时 `UMI_APP_AUTH_DEBUG=0`（或 `false`/`off`/`no`）。
 * - **运行时打开**（无需重建）：控制台执行 `globalThis.__DEVAULT_AUTH_DEBUG__ = true` 后刷新；
 *   或 `localStorage.setItem('devault_console_auth_debug','1')` 后刷新。
 * - **仅菜单/布局**：`localStorage.setItem('devault_console_layout_debug','1')`（见 `layout-debug.ts`）。
 */
export function authDebug(message: string, payload?: Record<string, unknown>): void {
  if (!debugEnabled()) return;
  if (payload !== undefined) {
    console.log(PREFIX, message, payload);
  } else {
    console.log(PREFIX, message);
  }
}

/**
 * 无条件输出一条探针（不受 `debugEnabled` 限制），用于确认打包是否含 `[devault:auth]` 与注入开关。
 * 仅在浏览器环境调用。
 */
export function authDebugBootProbe(where: string, extra?: Record<string, unknown>): void {
  if (typeof window === 'undefined') return;
  console.log(PREFIX, `boot:${where}`, {
    UMI_APP_AUTH_DEBUG: process.env.UMI_APP_AUTH_DEBUG,
    NODE_ENV: process.env.NODE_ENV,
    ...extra,
  });
}
