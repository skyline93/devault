const PREFIX = '[devault:auth]';

function debugEnabled(): boolean {
  if (process.env.NODE_ENV === 'development') return true;
  if (typeof window === 'undefined') return false;
  try {
    return window.localStorage?.getItem('devault_console_auth_debug') === '1';
  } catch {
    return false;
  }
}

/** 认证与会话排查日志：开发环境默认输出；生产可在控制台执行 `localStorage.setItem('devault_console_auth_debug','1')` 后刷新。 */
export function authDebug(message: string, payload?: Record<string, unknown>): void {
  if (!debugEnabled()) return;
  if (payload !== undefined) {
    console.debug(PREFIX, message, payload);
  } else {
    console.debug(PREFIX, message);
  }
}
