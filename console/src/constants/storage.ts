/**
 * localStorage：可选 **API 密钥 / 自动化** Bearer（§十六）；人机主路径为 **Cookie 会话**。
 */
export const STORAGE_BEARER_KEY = 'devault_bearer_token';

/** 与后端 `DEVAULT_CSRF_COOKIE_NAME` 默认一致（双提交 CSRF）。 */
export const CSRF_COOKIE_NAME = 'devault_csrf';

/** 可选；十五-07 顶栏租户选择器写入。未设置时由 API 使用默认 slug 租户。 */
export const STORAGE_TENANT_ID_KEY = 'devault_tenant_id';
