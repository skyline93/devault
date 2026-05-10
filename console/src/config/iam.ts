/**
 * External IAM (``iam/``) for Console login/register when ``UMI_APP_IAM_PREFIX`` is set
 * (e.g. ``/iam-api`` with dev proxy to IAM in ``config/config.ts``).
 */
export const IAM_API_PREFIX: string = (process.env.UMI_APP_IAM_PREFIX || '').replace(/\/$/, '');

export function isIamConsoleEnabled(): boolean {
  return IAM_API_PREFIX.length > 0;
}
