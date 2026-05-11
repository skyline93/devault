/** 连续两帧 rAF，给 React 一次提交 `@@initialState` 后再做路由跳转，减轻「守卫首帧无用户」竞态。 */
export function waitNextPaint(): Promise<void> {
  return new Promise((resolve) => {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => resolve());
    });
  });
}
