import { test, expect } from '@playwright/test';

async function fixture(page, { authenticated = true, reviewer = false } = {}) {
    const administrator = { id: 1, username: 'test-administrator', roles: [reviewer ? 'Reviewer' : 'Super Admin'], all_events: !reviewer, assigned_event_ids: [1] };
    const event = { id: 1, title: 'Test Conference', status: 'published', start_date: '2027-03-01T09:00:00+06:00', event_type: 'conference', venue: '' };
    const forms = [{ id: 7, event: 1, title: 'Delegate Registration', slug: 'delegates', description: '', form_type: 'custom', status: 'draft', fields: [], opens_at: null, closes_at: null, capacity: null, allow_multiple_submissions: false }];
    const writes = [];
    await page.route('**/api/**', async route => {
        const request = route.request(), path = new URL(request.url()).pathname.replace('/api', '');
        const method = request.method();
        const send = (body, status = 200) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
        if (path === '/admin/auth/me/') return send({ authenticated, administrator: authenticated ? administrator : null });
        if (path === '/admin/auth/csrf/') return send({ csrf_token: 'test-csrf-token' });
        if (path === '/admin/auth/login/') { authenticated = true; return send({ authenticated, administrator, csrf_token: 'rotated-test-token' }); }
        if (path === '/admin/auth/logout/') { authenticated = false; return route.fulfill({ status: 204 }); }
        if (!authenticated) return send({ detail: 'Administrator session required.' }, 403);
        if (path === '/admin/events/') return send({ count: 1, results: [event], next: null, previous: null });
        if (path === '/admin/forms/' && method === 'GET') return reviewer ? send({ detail: 'Access denied.' }, 403) : send({ count: forms.length, results: forms.map(form => ({ ...form, field_count: form.fields.length })), next: null, previous: null });
        if (path === '/admin/forms/' && method === 'POST') {
            const form = { ...forms[0], ...request.postDataJSON(), id: 8, status: 'draft' }; forms.push(form); writes.push(path); return send(form, 201);
        }
        const match = path.match(/^\/admin\/forms\/(\d+)\/(publish\/|duplicate\/)?$/);
        if (match) {
            const form = forms.find(item => item.id === Number(match[1]));
            if (!form) return send({ detail: 'Not found.' }, 404);
            if (method === 'GET') return send(form);
            writes.push(path);
            if (method === 'PATCH') {
                const payload = request.postDataJSON();
                if (payload.fields?.some(field => !field.label.trim())) return send({ fields: payload.fields.map(field => field.label.trim() ? {} : { label: ['This field may not be blank.'] }) }, 400);
                Object.assign(form, payload); return send(form);
            }
            if (match[2] === 'publish/') { form.status = 'published'; return send({ version: 1, schema: {} }, 201); }
            if (match[2] === 'duplicate/') {
                const copy = { ...structuredClone(form), ...request.postDataJSON(), id: 9, status: 'draft' }; forms.push(copy); return send(copy, 201);
            }
        }
        return send({ detail: 'Not found.' }, 404);
    });
    return { writes };
}
async function add(page, type = 'Short text') {
    await page.getByRole('button', { name: /Add your first question|^＋ Add question$/ }).click();
    await page.getByRole('dialog').getByRole('button', { name: new RegExp(type) }).click();
}

test('login protects deep links and reviewer routes deny form editing', async ({ page }) => {
    await fixture(page, { authenticated: false, reviewer: true });
    await page.goto('/admin/forms/7');
    await expect(page).toHaveURL(/\/admin\/login$/);
    await page.getByLabel('Username').fill('test-reviewer');
    await page.getByLabel('Password').fill('test-only-password');
    await page.getByRole('button', { name: /Sign in to your workspace/ }).click();
    await expect(page.getByRole('heading', { name: 'Access denied' })).toBeVisible();
    await expect(page.getByLabel('Form title')).toHaveCount(0);
});

test('creates a form, edits questions, handles server errors and publishes', async ({ page }) => {
    const { writes } = await fixture(page);
    await page.goto('/admin/forms');
    await page.getByRole('button', { name: '＋ Create form' }).click();
    const dialog = page.getByRole('dialog');
    await dialog.getByLabel('Form title').fill('Campus applications');
    await dialog.getByRole('button', { name: 'Create form', exact: true }).click();
    await expect(page).toHaveURL(/\/admin\/forms\/8$/);
    await add(page);
    await page.getByRole('button', { name: 'Save draft', exact: true }).click();
    await expect(page.getByLabel('Question label')).toHaveAttribute('aria-invalid', 'true');
    expect(writes.filter(path => path.includes('publish'))).toHaveLength(0);
    await page.getByLabel('Question label').fill('Full name');
    await page.getByLabel('Required question').check();
    await page.getByRole('button', { name: 'Publish form', exact: false }).click();
    await page.getByRole('button', { name: 'Save and publish' }).click();
    await expect(page.getByText('Version 1 published. Existing responses are preserved.')).toBeVisible();
    await page.getByRole('button', { name: 'Close form', exact: true }).click();
    await page.getByRole('button', { name: 'Save and close' }).click();
    await expect(page.getByText('Form closed. New responses are no longer accepted.')).toBeVisible();
    await page.getByRole('button', { name: 'Duplicate', exact: true }).click();
    await page.getByRole('button', { name: 'Create duplicate' }).click();
    await expect(page).toHaveURL(/\/admin\/forms\/9$/);
    await expect(page.getByLabel('Form title')).toHaveValue('Campus applications (copy)');
});

test('accessible reorder and unsaved navigation work at phone and desktop widths', async ({ page }, testInfo) => {
    await fixture(page);
    await page.goto('/admin/forms');
    await page.getByRole('link', { name: 'Open form builder' }).click();
    await add(page);
    await page.getByLabel('Question label').fill('First question');
    await add(page);
    await page.getByLabel('Question label').fill('Second question');
    await page.getByRole('button', { name: 'Move question 2 up' }).focus();
    await page.keyboard.press('Enter');
    await expect(page.getByRole('region', { name: 'Question 1', exact: true })).toContainText('Second question');
    await expect(page.getByText('Unsaved changes', { exact: true })).toBeVisible();
    page.once('dialog', dialog => dialog.dismiss());
    await page.goBack();
    await expect(page).toHaveURL(/\/admin\/forms\/7$/);
    await expect(page.getByLabel('Question label')).toHaveValue('Second question');
    for (const width of [1440, 768, 375]) {
        await page.setViewportSize({ width, height: 1000 });
        expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width + 1);
        await page.screenshot({ path: testInfo.outputPath(`builder-${width}.png`), fullPage: true });
    }
    await page.setViewportSize({ width: 1440, height: 1000 });
    page.once('dialog', dialog => dialog.accept());
    await page.getByRole('link', { name: '← All forms' }).click();
    await expect(page).toHaveURL(/\/admin\/forms\?event=1$/);
});

test('public pages keep their existing layout and never check admin sessions', async ({ page }) => {
    const sessionRequests = [];
    page.on('request', request => { if (request.url().includes('/admin/auth/')) sessionRequests.push(request.url()); });
    await page.goto('/events');
    await expect(page.getByRole('heading', { name: 'Events Archive' })).toBeVisible();
    expect(sessionRequests).toHaveLength(0);
    await expect(page.getByRole('navigation').first()).toBeVisible();
});
