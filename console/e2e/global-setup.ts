/**
 * 十五-22：为「切租户」冒烟准备第二租户。
 * 默认假定控制面 **dev-open**（未配置 IAM）；若配置了 IAM，请设置 **E2E_API_TOKEN** 为有效 JWT。
 */
import type { FullConfig } from '@playwright/test';

async function globalSetup(_config: FullConfig) {
  const api = process.env.E2E_API_ORIGIN || 'http://127.0.0.1:8000';
  const token = (process.env.E2E_API_TOKEN || '').trim();
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;
  const r = await fetch(`${api}/api/v1/tenants`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ name: 'E2E Second', slug: 'e2e-second' }),
  });
  if (r.status !== 201 && r.status !== 409) {
    const text = await r.text();
    throw new Error(`e2e global-setup: POST /tenants failed ${r.status}: ${text}`);
  }
}

export default globalSetup;
