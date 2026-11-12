import { test, expect } from '@playwright/test';

test('public schema, private uploads and safe retry against real Django', async ({ page }, testInfo) => {
    const authRequests = [];
    page.on('request', request => { if (request.url().includes('/admin/auth/')) authRequests.push(request.url()); });
    await page.addInitScript(() => {
        const NativeXHR = window.XMLHttpRequest;
        window.XMLHttpRequest = class extends NativeXHR {
            constructor() {
                super();
                this.addEventListener('load', event => {
                    if (!window.lostReceipt && this.responseURL.includes('/submit/') && this.status === 201) {
                        window.lostReceipt = JSON.parse(this.responseText).reference_number;
                        event.stopImmediatePropagation();
                        this.onerror?.(new ProgressEvent('error'));
                    }
                });
            }
        };
    });
    let requests = 0;
    page.on('request', request => { if (request.url().includes('/submit/')) requests++; });
    await page.goto('/events/isolated-test-conference/register');
    await expect(page.getByRole('heading', { name: 'Executive Board Application', exact: true })).toBeVisible();
    await page.locator('article').filter({ has: page.getByRole('heading', { name: 'Delegate Registration', exact: true }) }).getByRole('link', { name: /Start application/ }).click();
    await page.getByRole('textbox', { name: 'Full name', exact: true }).fill('Integration applicant');
    await page.getByRole('textbox', { name: 'Email', exact: true }).fill('browser-test@example.invalid');
    await page.getByRole('textbox', { name: 'Phone', exact: true }).fill('+8801700000000');
    await page.getByRole('textbox', { name: 'Institution', exact: true }).fill('Test institution');
    await page.getByRole('combobox', { name: 'Academic year', exact: true }).selectOption('1');
    await page.getByRole('checkbox', { name: 'General Assembly', exact: true }).check();
    await page.getByRole('radio', { name: 'I do not need accommodation', exact: true }).check();
    await page.getByLabel('Passport-size photo', { exact: true }).setInputFiles(process.env.MUNC_E2E_PHOTO);
    await page.getByLabel('Payment screenshot', { exact: true }).setInputFiles(process.env.MUNC_E2E_PHOTO);
    await page.getByRole('checkbox', { name: 'Consent to data processing I agree', exact: true }).check();
    for (const width of [1440, 375]) {
        await page.setViewportSize({ width, height: 900 });
        expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width + 1);
        await page.screenshot({ path: testInfo.outputPath(`public-form-${width}.png`), fullPage: true });
    }
    await page.getByRole('button', { name: 'Submit application' }).click();
    await expect(page.getByRole('heading', { name: 'Confirmation not yet received' })).toBeVisible();
    await expect(page.getByRole('textbox', { name: 'Full name', exact: true })).toBeDisabled();
    const firstReference = await page.evaluate(() => window.lostReceipt);
    await page.getByRole('button', { name: 'Retry same application' }).click();
    await expect(page).toHaveURL(/\/confirmation$/);
    await expect(page.getByLabel('Registration reference number')).toHaveText(firstReference);
    expect(requests).toBe(2);
    await page.reload();
    await expect(page.getByLabel('Registration reference number')).toHaveText(firstReference);
    const storage = await page.evaluate(() => JSON.stringify({ ...sessionStorage }));
    expect(storage).not.toContain('browser-test@example.invalid');
    expect(storage).not.toContain('+8801700000000');
    expect(authRequests).toEqual([]);
});
