/** localStorage：与 REST 对齐的 Bearer；不落 Cookie、不走 HTTP Basic。 */
export const STORAGE_BEARER_KEY = 'devault_bearer_token';

/** 可选；十五-07 顶栏租户选择器写入。未设置时由 API 使用默认 slug 租户。 */
export const STORAGE_TENANT_ID_KEY = 'devault_tenant_id';
