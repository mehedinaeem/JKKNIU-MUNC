import { test, expect } from '@playwright/test';

test('email admin drafts, recipient counts, previews, test queue, schedule, pause, cancel and templates', async ({ page }, testInfo) => {
    await page.goto('/admin/email');
    await page.getByLabel('Username').fill(process.env.MUNC_E2E_USERNAME);
    await page.getByLabel('Password').fill(process.env.MUNC_E2E_PASSWORD);
    await page.getByRole('button', { name: /Sign in to your workspace/ }).click();
    await expect(page.getByRole('heading', { name: 'Email overview', exact: true })).toBeVisible();
    await expect(page.getByText(/Email transport is disabled/)).toBeVisible();
    await page.getByRole('link', { name: 'Campaigns', exact: true }).click();
    await page.getByRole('link', { name: 'New campaign', exact: true }).click();
    await page.getByRole('textbox', { name: 'Campaign name', exact: true }).fill('Operational conference briefing');
    await page.getByRole('combobox', { name: 'Event', exact: true }).selectOption({ label: 'Isolated test conference' });
    await page.getByRole('combobox', { name: 'Registration category', exact: true }).selectOption({ label: 'Review fixture' });
    await expect(page.getByText('1 unique eligible recipients', { exact: true })).toBeVisible();
    await page.getByRole('textbox', { name: 'Email subject', exact: true }).fill('Briefing for {{event_name}}');
    await page.getByRole('textbox', { name: 'Formatted email', exact: true }).fill('Hello {{full_name}}, please attend our event briefing.');
    await page.getByRole('textbox', { name: 'Plain-text fallback', exact: true }).fill('Hello {{full_name}}, please attend our event briefing.');
    await page.getByRole('button', { name: 'Save draft', exact: true }).click();
    await expect(page).toHaveURL(/\/admin\/email\/campaigns\/\d+$/);
    const campaignId = page.url().split('/').at(-1);
    await page.getByRole('button', { name: 'Preview', exact: true }).click();
    await expect(page.getByRole('dialog').getByText('Briefing for Isolated test conference', { exact: true })).toBeVisible();
    await expect(page.getByTitle('Sanitized email preview')).toHaveAttribute('sandbox', '');
    await expect(page.frameLocator('iframe[title="Sanitized email preview"]').getByText('Hello Review fixture applicant, please attend our event briefing.', { exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'Close dialog', exact: true }).click();
    await page.getByRole('button', { name: 'Send test to my admin email' }).click();
    await expect(page.getByText(/Test email queued for your administrator email/)).toBeVisible();
    const jobs = await (await page.request.get(`${process.env.MUNC_E2E_REAL_API}/admin/email/messages/`)).json();
    expect(jobs.results.some(job => job.message_type === 'admin_test' && job.status === 'pending')).toBe(true);
    await page.getByRole('button', { name: 'Schedule…', exact: true }).click();
    const day = new Date(Date.now() + 2 * 86400000).toISOString().slice(0, 10);
    await page.getByLabel('Scheduled time (Asia/Dhaka)').fill(`${day}T09:00`);
    await page.getByRole('button', { name: 'Confirm', exact: true }).click();
    await expect(page.getByText('scheduled', { exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'Pause unsent messages' }).click();
    await expect(page.getByText('paused', { exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'Resume', exact: true }).click();
    await expect(page.getByText('scheduled', { exact: true })).toBeVisible();
    for (const width of [1440, 768, 375]) {
        await page.setViewportSize({ width, height: 1000 });
        expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width + 1);
        await page.screenshot({ path: testInfo.outputPath(`email-${width}.png`), fullPage: true });
    }
    await page.getByRole('button', { name: 'Cancel unsent messages…' }).click();
    await page.getByRole('button', { name: 'Confirm', exact: true }).click();
    await expect(page.getByText('cancelled', { exact: true })).toBeVisible();
    const campaign = await (await page.request.get(`${process.env.MUNC_E2E_REAL_API}/admin/email/campaigns/${campaignId}/`)).json();
    expect(campaign.snapshot_at).toBeNull(); // No worker runs and no provider is contacted.
    expect(campaign.status).toBe('cancelled');
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.getByRole('link', { name: 'Templates', exact: true }).click();
    await page.getByRole('button', { name: /^Registration Confirmation/ }).click();
    await expect(page.getByRole('textbox', { name: 'Template subject', exact: true })).toHaveValue('Registration Received — {{event_name}}');
    await page.getByRole('button', { name: 'Preview example', exact: true }).click();
    await expect(page.getByRole('dialog').getByText('Registration Received — Example MUN Conference', { exact: true })).toBeVisible();
});
