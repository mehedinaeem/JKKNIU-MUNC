import { readFileSync } from 'node:fs';
import { test, expect } from '@playwright/test';

test('assigned reviewer can search, review, download and export without accessing other events', async ({ page }, testInfo) => {
    await page.goto('/admin/submissions');
    await page.getByLabel('Username').fill(process.env.MUNC_E2E_REVIEWER);
    await page.getByLabel('Password').fill(process.env.MUNC_E2E_PASSWORD);
    await page.getByRole('button', { name: /Sign in to your workspace/ }).click();
    await expect(page.getByRole('heading', { name: 'Applications', exact: true })).toBeVisible();
    await page.getByRole('searchbox', { name: 'Search applications' }).fill('review-fixture@example.invalid');
    await page.getByRole('button', { name: 'Search', exact: true }).click();
    await expect(page.getByRole('table').getByRole('row')).toHaveCount(2);
    const hidden = await page.request.get(`${process.env.MUNC_E2E_REAL_API}/admin/submissions/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa/`);
    expect(hidden.status()).toBe(404);
    const hiddenExport = await page.request.get(`${process.env.MUNC_E2E_REAL_API}/admin/submissions/export/?search=hidden%40example.invalid`);
    expect(hiddenExport.status()).toBe(200);
    expect(await hiddenExport.text()).not.toContain('hidden@example.invalid');
    for (const kind of ['csv', 'xlsx']) {
        const pending = page.waitForEvent('download');
        await page.getByRole('button', { name: `Export ${kind.toUpperCase()}` }).click();
        const download = await pending;
        expect(download.suggestedFilename()).toBe(`munc-applications.${kind}`);
        const bytes = readFileSync(await download.path());
        if (kind === 'csv') { expect(bytes.toString()).toContain('Review fixture applicant'); expect(bytes.toString()).not.toContain('Hidden applicant'); }
        else expect(bytes.subarray(0, 2).toString()).toBe('PK');
    }
    await page.getByRole('table').getByRole('link').click();
    await expect(page.getByRole('heading', { name: 'Submitted answers' })).toBeVisible();
    await expect(page.getByText('Review fixture applicant', { exact: true })).toBeVisible();
    await expect(page.getByText('General Assembly', { exact: true })).toBeVisible();
    const filePending = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Download private file' }).click();
    expect((await filePending).suggestedFilename()).toMatch(/\.png$/);
    await page.getByLabel('Review status', { exact: true }).selectOption('under_review');
    await page.getByRole('button', { name: 'Update status' }).click();
    await expect(page.getByText('Application status updated.', { exact: true })).toBeVisible();
    await page.getByRole('textbox', { name: 'Note', exact: true }).fill('Interview availability checked. Private reviewer assessment.');
    await page.getByRole('button', { name: 'Add private note' }).click();
    await expect(page.getByText('Private reviewer note added.', { exact: true })).toBeVisible();
    await page.reload();
    await expect(page.getByText('Interview availability checked. Private reviewer assessment.', { exact: true })).toBeVisible();
    await expect(page.getByText('Submitted → Under review', { exact: true })).toBeVisible();
    for (const width of [1440, 768, 375]) {
        await page.setViewportSize({ width, height: 1000 });
        expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width + 1);
        await page.screenshot({ path: testInfo.outputPath(`review-${width}.png`), fullPage: true });
    }
    await page.getByRole('link', { name: '← Applications' }).click();
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(376);
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.getByRole('link', { name: 'Overview', exact: true }).click();
    await expect(page.getByRole('link', { name: 'Total events 1', exact: true })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Applications under review 1', exact: true })).toBeVisible();
});
