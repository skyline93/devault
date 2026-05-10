import { test, expect } from '@playwright/test';

test.describe('console smoke（十五-22）', () => {
  test('登录 → 作业中心 → 可选切租户 → 备份向导页', async ({ page }) => {
    const token = process.env.E2E_API_TOKEN || 'changeme';

    await page.goto('/user/integration');
    await page.getByPlaceholder(/Bearer Token/).fill(token);
    await page.getByRole('button', { name: '登录' }).click();
    await expect(page).toHaveURL(/\/overview\/welcome/);

    await page.goto('/backup/jobs');
    await expect(page.getByText('作业中心').first()).toBeVisible();
    await expect(page.locator('.ant-table')).toBeVisible();

    const header = page.locator('.ant-layout-header');
    const tenantSelect = header.locator('.ant-select').first();
    await tenantSelect.click();
    const options = page.locator('.ant-select-dropdown .ant-select-item-option');
    const n = await options.count();
    if (n >= 2) {
      await options.nth(1).click();
      await expect(page.locator('.ant-table')).toBeVisible({ timeout: 30_000 });
    }

    await page.goto('/backup/run');
    await expect(page.getByText('发起备份').first()).toBeVisible();
    await expect(page.getByText('选择方式')).toBeVisible();
    await expect(page.getByText('填写参数')).toBeVisible();
    await expect(page.getByText('确认并入队')).toBeVisible();
  });
});
