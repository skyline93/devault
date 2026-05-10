/** localStorage：可选 IAM **access_token**（Bearer）。 */
export const STORAGE_BEARER_KEY = 'devault_bearer_token';

/** 历史 CSRF Cookie 名；若浏览器仍有旧 Cookie，写入请求头以兼容（控制面已不再签发）。 */
export const CSRF_COOKIE_NAME = 'devault_csrf';

/** 可选；十五-07 顶栏租户选择器写入。未设置时由 API 使用默认 slug 租户。 */
export const STORAGE_TENANT_ID_KEY = 'devault_tenant_id';
