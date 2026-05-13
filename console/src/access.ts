import { layoutDebug } from '@/utils/layout-debug';

let lastAccessDebugJson = '';

/**
 * 与 §四 RBAC 对齐：`canAdmin` / `canWrite`；`auditor` 仅只读（十五-05）。
 * 路由级 `access` 在后续页面（作业写操作等）上按需声明。
 */
export default function access(initialState: {
  currentUser?: API.CurrentUser;
  canAdmin?: boolean;
  canWrite?: boolean;
  canInviteMembers?: boolean;
  canPlatformStorage?: boolean;
  needsPasswordChange?: boolean;
}) {
  const { currentUser, canAdmin, canWrite, canInviteMembers, canPlatformStorage, needsPasswordChange } =
    initialState ?? {};
  const snapshot = {
    canAdmin: Boolean(canAdmin),
    canWrite: Boolean(canWrite),
    canInviteMembers: Boolean(canInviteMembers),
    canPlatformStorage: Boolean(canPlatformStorage),
    needsPasswordChange: Boolean(needsPasswordChange),
    isAuditor: currentUser?.role === 'auditor',
  };
  const accessLogPayload = {
    hasCurrentUser: Boolean(currentUser),
    role: currentUser?.role,
    needsMfa: currentUser?.needs_mfa,
    needsPasswordChange: snapshot.needsPasswordChange,
    ...snapshot,
  };
  const nextJson = JSON.stringify(accessLogPayload);
  if (lastAccessDebugJson !== nextJson) {
    lastAccessDebugJson = nextJson;
    layoutDebug('access:computed', accessLogPayload);
  }
  return snapshot;
}
