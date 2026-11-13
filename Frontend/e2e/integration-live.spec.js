import { readFileSync } from 'node:fs';
import { test, expect } from '@playwright/test';

// One continuous workflow: all records and files live in the runner's disposable DB.
test('National MUN: admin creates event/form, visitor uploads, admin reviews and exports', async ({ page, browser }, testInfo) => {
    test.setTimeout(90000);
    const eventTitle = 'National MUN Conference integration 2027';
    const slug = 'national-mun-conference-integration-2027';
    const formSlug = 'integration-delegate-registration';
    await page.goto('/admin/events/new');
    await page.getByLabel('Username').fill(process.env.MUNC_E2E_USERNAME);
    await page.getByLabel('Password').fill(process.env.MUNC_E2E_PASSWORD);
    await page.getByRole('button', { name: /Sign in to your workspace/ }).click();
    await page.getByRole('textbox', { name: 'Event title', exact: true }).fill(eventTitle);
    await page.getByRole('textbox', { name: 'Event type', exact: true }).fill('National MUN');
    await page.getByRole('textbox', { name: 'Venue', exact: true }).fill('JKKNIU campus');
    await page.getByRole('textbox', { name: 'Short description', exact: true }).fill('A complete registration workflow for a National MUN conference.');
    await page.getByRole('textbox', { name: 'Full description', exact: true }).fill('Conference information supplied by the event administrator.');
    const day = offset => new Date(Date.now() + offset * 86400000).toISOString().slice(0, 10);
    await page.getByLabel('Event starts (Asia/Dhaka)').fill(`${day(90)}T09:00`);
    await page.getByLabel('Registration opens (Asia/Dhaka)').fill(`${day(-2)}T09:00`);
    await page.getByLabel('Registration closes (Asia/Dhaka)').fill(`${day(30)}T18:00`);
    await page.getByRole('combobox', { name: 'Status', exact: true }).selectOption('published');
    await page.getByRole('button', { name: 'Create event', exact: true }).click();
    await expect(page).toHaveURL(/\/admin\/events\/\d+$/);
    const eventId = page.url().split('/').at(-1);
    await page.getByRole('link', { name: 'Registration forms →', exact: true }).click();
    await page.getByRole('button', { name: '＋ Create form' }).click();
    await page.getByRole('dialog').getByRole('textbox', { name: 'Form title', exact: true }).fill('Integration Delegate Registration');
    await page.getByRole('dialog').getByRole('button', { name: 'Create form', exact: true }).click();
    await expect(page).toHaveURL(/\/admin\/forms\/\d+$/);
    for (const [type, label] of [['Short text', 'Full name'], ['Email', 'Email'], ['File upload', 'Passport photo']]) {
        await page.getByRole('button', { name: /Add your first question|^＋ Add question$/ }).click();
        await page.getByRole('dialog').getByRole('button', { name: new RegExp(type) }).click();
        await page.getByLabel('Question label').fill(label);
        await page.getByLabel('Required question').check();
    }
    await page.getByRole('button', { name: 'Publish form', exact: false }).click();
    await page.getByRole('button', { name: 'Save and publish' }).click();
    await expect(page.getByText('Version 1 published. Existing responses are preserved.')).toBeVisible();
    // A second category must not force applicants into the delegate application.
    await page.getByRole('button', { name: 'Duplicate', exact: true }).click();
    await page.getByLabel('New form title').fill('Integration Executive Board Application');
    await page.getByLabel('New form slug').fill('integration-executive-board');
    await page.getByRole('button', { name: 'Create duplicate' }).click();
    await expect(page.getByRole('dialog', { name: 'Duplicate form' })).not.toBeVisible();
    await page.getByRole('button', { name: 'Publish form', exact: false }).click();
    await page.getByRole('button', { name: 'Save and publish' }).click();
    await expect(page.getByText('Version 1 published. Existing responses are preserved.')).toBeVisible();
    const visitorContext = await browser.newContext();
    try {
        const visitor = await visitorContext.newPage();
        await visitor.goto('http://127.0.0.1:4173/');
        await expect(visitor.getByRole('region', { name: 'Upcoming events', exact: true }).getByRole('link', { name: `Register for ${eventTitle}`, exact: true })).toBeVisible();
        for (const width of [1440, 768, 375]) {
            await visitor.setViewportSize({ width, height: 900 });
            expect(await visitor.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width + 1);
            await visitor.getByRole('region', { name: 'Upcoming events', exact: true }).screenshot({ path: testInfo.outputPath(`home-upcoming-${width}.png`) });
        }
        await visitor.setViewportSize({ width: 1280, height: 900 });
        await visitor.goto('http://127.0.0.1:4173/events');
        await expect(visitor.getByRole('region', { name: 'Upcoming events', exact: true }).getByRole('heading', { name: eventTitle, exact: true })).toBeVisible();
        await visitor.getByRole('link', { name: `View details: ${eventTitle}`, exact: true }).click();
        await expect(visitor.getByRole('heading', { name: eventTitle, exact: true })).toBeVisible();
        await visitor.getByRole('link', { name: 'Register now →', exact: true }).click();
        await expect(visitor.getByRole('heading', { name: 'Integration Executive Board Application', exact: true })).toBeVisible();
        await visitor.locator('article').filter({ has: visitor.getByRole('heading', { name: 'Integration Delegate Registration', exact: true }) }).getByRole('link', { name: /Start application/ }).click();
        await visitor.getByRole('button', { name: 'Submit application' }).click();
        await expect(visitor.locator('section[role=alert]')).toContainText('This question is required.');
        await visitor.getByRole('textbox', { name: 'Full name', exact: true }).fill('National MUN applicant');
        await visitor.getByRole('textbox', { name: 'Email', exact: true }).fill('national-mun@example.invalid');
        await visitor.getByLabel('Passport photo', { exact: true }).setInputFiles(process.env.MUNC_E2E_PHOTO);
        const submitted = visitor.waitForResponse(response => response.url().endsWith(`/forms/${formSlug}/submit/`) && response.request().method() === 'POST');
        await visitor.getByRole('button', { name: 'Submit application' }).click();
        const receipt = await (await submitted).json();
        expect(Object.keys(receipt).sort()).toEqual(['message', 'reference_number']);
        await expect(visitor).toHaveURL(/\/confirmation$/);
        await expect(visitor.getByLabel('Registration reference number')).toHaveText(receipt.reference_number);
        const base = process.env.MUNC_E2E_REAL_API;
        const schema = await (await visitor.request.get(`${base}/forms/${formSlug}/`)).json();
        await page.goto(`/admin/submissions?search=${receipt.reference_number}`);
        await page.getByRole('table').getByRole('link', { name: receipt.reference_number }).click();
        await expect(page.getByText('National MUN applicant', { exact: true })).toBeVisible();
        const id = page.url().split('/').at(-1);
        const detail = await (await page.request.get(`${base}/admin/submissions/${id}/`)).json();
        expect(detail.files).toHaveLength(1);
        expect(detail.files[0].file_size).toBeGreaterThan(0);
        expect(detail.files[0].download_url).toMatch(/^\/api\/submission-files\/\d+\/$/);
        expect(JSON.stringify(receipt)).not.toContain('national-mun@example.invalid');
        const privateDownload = page.waitForEvent('download');
        await page.getByRole('button', { name: 'Download private file' }).click();
        const storedPhoto = await privateDownload;
        expect(readFileSync(await storedPhoto.path()).subarray(1, 4).toString()).toBe('PNG');
        expect((await visitor.request.get(`${base}${detail.files[0].download_url.replace(/^\/api/, '')}`)).status()).toBe(403);
        await page.getByLabel('Review status', { exact: true }).selectOption('approved');
        await page.getByRole('button', { name: 'Update status' }).click();
        await expect(page.getByText('Application status updated.')).toBeVisible();
        const reviewed = await (await page.request.get(`${base}/admin/submissions/${id}/`)).json();
        expect(reviewed.status).toBe('approved');
        expect(reviewed.history.at(-1).status).toBe('approved');
        await page.goto(`/admin/submissions?search=${receipt.reference_number}`);
        for (const kind of ['CSV', 'XLSX']) {
            const downloaded = page.waitForEvent('download');
            await page.getByRole('button', { name: `Export ${kind}` }).click();
            const file = await downloaded;
            expect((await file.failure())).toBeNull();
            if (kind === 'CSV') expect(readFileSync(await file.path()).toString()).toContain(receipt.reference_number);
        }
        // Server validation is checked independently of browser usability checks.
        expect((await visitor.request.get(`${base}/admin/submissions/`)).status()).toBe(403);
        expect((await visitor.request.post(`${base}/forms/${formSlug}/submit/`, { data: { applicant_email: 'missing@example.invalid', version: schema.version, answers: {} } })).status()).toBe(400);
        const fileField = schema.schema.fields.find(field => field.field_type === 'file');
        const payload = { applicant_email: 'national-mun@example.invalid', version: schema.version, answers: detail.answers };
        const multipart = file => ({ payload: JSON.stringify(payload), [fileField.key]: file });
        expect((await visitor.request.post(`${base}/forms/${formSlug}/submit/`, { multipart: multipart({ name: 'unsafe.html', mimeType: 'text/html', buffer: Buffer.from('<html>unsafe</html>') }) })).status()).toBe(400);
        expect((await visitor.request.post(`${base}/forms/${formSlug}/submit/`, { multipart: multipart({ name: 'photo.png', mimeType: 'image/png', buffer: readFileSync(process.env.MUNC_E2E_PHOTO) }) })).status()).toBe(400);
        const finalList = await (await page.request.get(`${base}/admin/submissions/?registration_form=${schema.id}`)).json();
        expect(finalList.count).toBe(1);
        const csrf = await (await page.request.get(`${base}/admin/auth/csrf/`)).json();
        const closed = await page.request.patch(`${base}/admin/events/${eventId}/`, { data: { registration_end: new Date(Date.now() - 60000).toISOString() }, headers: { 'X-CSRFToken': csrf.csrf_token } });
        expect(closed.status()).toBe(200);
        expect((await visitor.request.post(`${base}/forms/${formSlug}/submit/`, { multipart: multipart({ name: 'photo.png', mimeType: 'image/png', buffer: readFileSync(process.env.MUNC_E2E_PHOTO) }) })).status()).toBe(400);
        await visitor.goto(`http://127.0.0.1:4173/events/${slug}`);
        await expect(visitor.getByText('Registration has closed.', { exact: true })).toBeVisible();
        await expect(visitor.getByRole('link', { name: 'Register now →' })).toHaveCount(0);
        for (const width of [1440, 768, 375]) {
            await visitor.setViewportSize({ width, height: 900 });
            expect(await visitor.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width + 1);
            await visitor.screenshot({ path: testInfo.outputPath(`event-${width}.png`), fullPage: true });
        }
        const ended = await page.request.patch(`${base}/admin/events/${eventId}/`, { data: { start_date: new Date(Date.now() - 30000).toISOString() }, headers: { 'X-CSRFToken': csrf.csrf_token } });
        expect(ended.status()).toBe(200);
        await visitor.goto('http://127.0.0.1:4173/events');
        await expect(visitor.getByRole('region', { name: 'Past events', exact: true }).getByRole('heading', { name: eventTitle, exact: true })).toBeVisible();
        await expect(visitor.getByRole('region', { name: 'Upcoming events', exact: true }).getByRole('heading', { name: eventTitle, exact: true })).toHaveCount(0);
        await visitor.goto('http://127.0.0.1:4173/');
        await expect(visitor.getByRole('region', { name: 'Upcoming events', exact: true }).getByRole('heading', { name: eventTitle, exact: true })).toHaveCount(0);
    } finally { await visitorContext.close(); }
});
