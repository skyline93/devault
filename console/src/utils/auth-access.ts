import { STORAGE_IAM_PWD_CHANGE_REQUIRED } from '@/constants/storage';

/** IAM 登录后待完成「强制改密」时写入；改密成功或登出时清除。 */
export function readPasswordChangePending(): boolean {
  if (typeof window === 'undefined') return false;
  return localStorage.getItem(STORAGE_IAM_PWD_CHANGE_REQUIRED) === '1';
}

export function setPasswordChangePending(value: boolean): void {
  if (typeof window === 'undefined') return;
  if (value) localStorage.setItem(STORAGE_IAM_PWD_CHANGE_REQUIRED, '1');
  else localStorage.removeItem(STORAGE_IAM_PWD_CHANGE_REQUIRED);
}

export function computeSessionAccessFlags(currentUser: API.CurrentUser | undefined): {
  needsPasswordChange: boolean;
  canAdmin: boolean;
  canWrite: boolean;
  canInviteMembers: boolean;
  canPlatformStorage: boolean;
} {
  const pwdPending = readPasswordChangePending();
  const gated = Boolean(currentUser?.needs_mfa) || pwdPending;
  return {
    needsPasswordChange: pwdPending,
    canAdmin: Boolean(currentUser && !gated && currentUser.role === 'admin'),
    canWrite: Boolean(currentUser && !gated && (currentUser.role === 'admin' || currentUser.role === 'operator')),
    canInviteMembers: Boolean(
      currentUser && !gated && currentUser.tenants?.some((t) => t.membership_role === 'tenant_admin'),
    ),
    canPlatformStorage: Boolean(
      currentUser && !gated && currentUser.role === 'admin' && currentUser.principal_kind === 'platform',
    ),
  };
}
