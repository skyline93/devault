/**
 * 登录页路径（401 重定向、登出、会话守卫等与 `config/config.ts` 里 `layout: false` 的
 * `/user/login` 等公开路由应对齐）。
 */
export const LOGIN_PATH = '/user/login';

/** IAM 强制改密页；须改密期间仅允许本页与 `LOGIN_PATH`（见 `RequireSession`）。 */
export const CHANGE_PASSWORD_PATH = '/user/change-password';
