/**
 * 与 §四 RBAC 对齐：`canAdmin` / `canWrite`；`auditor` 仅只读（十五-05）。
 * 路由级 `access` 在后续页面（作业写操作等）上按需声明。
 */
export default function access(initialState: {
  currentUser?: API.CurrentUser;
  canAdmin?: boolean;
  canWrite?: boolean;
}) {
  const { currentUser, canAdmin, canWrite } = initialState ?? {};
  return {
    canAdmin: Boolean(canAdmin),
    canWrite: Boolean(canWrite),
    isAuditor: currentUser?.role === 'auditor',
  };
}
