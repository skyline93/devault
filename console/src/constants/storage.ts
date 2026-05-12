/** localStorage：可选 IAM **access_token**（Bearer）。 */
export const STORAGE_BEARER_KEY = 'devault_bearer_token';

/** localStorage：IAM **refresh_token**（改密后刷新 access 等）。 */
export const STORAGE_REFRESH_TOKEN_KEY = 'devault_refresh_token';

/** localStorage：IAM 已登录但 **必须** 先完成改密（与 `must_change_password` 对齐）。 */
export const STORAGE_IAM_PWD_CHANGE_REQUIRED = 'devault_iam_must_change_password';

/** 历史 CSRF Cookie 名；若浏览器仍有旧 Cookie，写入请求头以兼容（控制面已不再签发）。 */
export const CSRF_COOKIE_NAME = 'devault_csrf';

/** 可选；十五-07 顶栏租户选择器写入。未设置时由 API 使用默认 slug 租户。 */
export const STORAGE_TENANT_ID_KEY = 'devault_tenant_id';
