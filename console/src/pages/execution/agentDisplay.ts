/** 用户可见的 Agent 主标签：优先主机名，否则使用回退文案（不传裸 UUID 作主文案）。 */
export function agentPrimaryLabel(hostname: string | null | undefined, fallbackWhenEmpty: string): string {
  const h = hostname?.trim();
  return h && h.length > 0 ? h : fallbackWhenEmpty;
}
