/** IAM `assert_password_policy`：至少 12 字符；生成可读性较强的初始密码。 */
const MIN_LEN = 12;

export function generateInitialPassword(): string {
  const upper = 'ABCDEFGHJKMNPQRSTUVWXYZ';
  const lower = 'abcdefghjkmnpqrstuvwxyz';
  const digit = '23456789';
  const sym = '@#$%';
  const all = upper + lower + digit + sym;
  const pick = (pool: string, u: number) => pool[u % pool.length];

  if (typeof crypto !== 'undefined' && typeof crypto.getRandomValues === 'function') {
    const buf = new Uint8Array(48);
    crypto.getRandomValues(buf);
    let i = 0;
    const parts = [pick(upper, buf[i++]), pick(lower, buf[i++]), pick(digit, buf[i++]), pick(sym, buf[i++])];
    while (parts.join('').length < MIN_LEN) {
      parts.push(pick(all, buf[i++ % buf.length]));
    }
    return parts.join('');
  }
  const t = Date.now().toString(36);
  return `Aa1$${t}xxxxxx`.slice(0, Math.max(MIN_LEN, 16)).padEnd(MIN_LEN, 'x');
}
