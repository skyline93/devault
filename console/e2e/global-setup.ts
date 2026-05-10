/**
 * 十五-22：为「切租户」冒烟准备第二租户（admin legacy token）。
 * 依赖可从宿主机访问的 API（Compose 映射 **:8000**）。
 */
import type { FullConfig } from '@playwright/test';

async function globalSetup(_config: FullConfig) {
  const api = process.env.E2E_API_ORIGIN || 'http://127.0.0.1:8000';
  const token = process.env.E2E_API_TOKEN || 'changeme';
  const r = await fetch(`${api}/api/v1/tenants`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ name: 'E2E Second', slug: 'e2e-second' }),
  });
  if (r.status !== 201 && r.status !== 409) {
    const text = await r.text();
    throw new Error(`e2e global-setup: POST /tenants failed ${r.status}: ${text}`);
  }
}

export default globalSetup;
