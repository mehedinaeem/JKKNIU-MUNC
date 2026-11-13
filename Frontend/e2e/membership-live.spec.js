import { test, expect } from '@playwright/test';

test('membership application, independent officer approval, private activation, profile and suspension', async ({ browser }, testInfo) => {
    const adminContext = await browser.newContext();
    const memberContext = await browser.newContext();
    const admin = await adminContext.newPage();
    const visitor = await memberContext.newPage();
    try {
        await visitor.goto('/join');
        await expect(visitor.getByRole('heading', { name: 'Your place in the conversation' })).toBeVisible();
        await visitor.getByRole('link', { name: /Start an application/ }).click();
        await visitor.getByLabel('University registration number').fill('MEMBER-E2E-001');
        await visitor.getByLabel(/I consent to checking/).check();
        await visitor.getByRole('button', { name: 'Show my student details' }).click();
        await expect(visitor.getByRole('heading', { name: 'Is this you?' })).toBeVisible();
        await expect(visitor.getByText('Academic session', { exact: true })).toHaveCount(0);
        await expect(visitor.getByText('Membership Test Student', { exact: true })).toBeVisible();
        await visitor.getByLabel(/Yes, this is me/).check();
        await visitor.getByRole('radio', { name: 'No, I would like to join' }).check();
        await visitor.getByLabel('Email address').fill('membership-e2e@example.invalid');
        await visitor.getByLabel('Why would you like to join MUNC?').fill('I want to contribute to diplomacy and join our university club.');
        await visitor.getByRole('radio', { name: 'Yes, I am already a member' }).check();
        await expect(visitor.getByLabel('Why would you like to join MUNC?')).toHaveCount(0);
        await visitor.getByRole('radio', { name: 'No, I would like to join' }).check();
        await visitor.getByLabel('Why would you like to join MUNC?').fill('I want to contribute to diplomacy and join our university club.');
        for (const width of [375, 768, 1440]) {
            await visitor.setViewportSize({ width, height: 1000 });
            await visitor.evaluate(() => window.scrollTo(0, 0));
            expect(await visitor.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width+1);
            await visitor.screenshot({ path: testInfo.outputPath(`application-confirm-${width}.png`), fullPage: true });
        }
        await visitor.getByRole('button', { name: 'Submit application' }).click();
        await expect(visitor.getByRole('status')).toContainText('Application request received');
        await admin.goto('/admin/members/applications');
        await admin.getByLabel('Username').fill(process.env.MUNC_E2E_USERNAME);
        await admin.getByLabel('Password').fill(process.env.MUNC_E2E_PASSWORD);
        await admin.getByRole('button', { name: /Sign in to your workspace/ }).click();
        await expect(admin.getByRole('heading', { name: 'Membership applications', exact: true })).toBeVisible();
        await admin.getByRole('button', { name: 'Review application' }).click();
        admin.on('dialog', dialog => dialog.accept());
        await admin.getByRole('button', { name: 'Approve', exact: true }).click();
        await admin.getByRole('link', { name: 'Verify ownership and create member' }).click();
        await admin.getByRole('button', { name: 'Create member', exact: true }).click();
        await admin.getByLabel('University registration number').fill('MEMBER-E2E-001');
        await admin.getByRole('button', { name: 'Check authorized student record' }).click();
        await expect(admin.getByText('Membership Test Student', { exact: true })).toBeVisible();
        await expect(admin.getByText('MEMBER-ST-001', { exact: true })).toBeVisible();
        await admin.getByLabel('Membership role').selectOption({ label: 'General Member' });
        await admin.getByLabel('Independent identity confirmation evidence', { exact: true }).fill('In-person inspection of university ID and student identity.');
        await admin.getByLabel(/I independently confirmed/).check();
        await admin.getByRole('button', { name: 'Create inactive member account' }).click();
        await admin.getByRole('button', { name: 'Manage', exact: true }).click();
        await admin.getByLabel('Identity evidence / decision reason').fill('Student identified independently in person at club office.');
        await admin.getByLabel('Private invitation delivery').selectOption('in_person');
        await admin.getByRole('button', { name: 'Issue / replace activation invitation' }).click();
        const privateUrl = await admin.getByLabel('Private invitation link').inputValue();
        expect(privateUrl).toContain('/join/activate#token=');
        const invitationUrl = new URL(privateUrl);
        await visitor.goto(invitationUrl.pathname + invitationUrl.hash);
        await expect(visitor.getByText('Private invitation loaded. Choose a strong, unique password.')).toBeVisible();
        await expect(visitor).not.toHaveURL(/#token=/);
        const password = 'Membership!isolated-secure-pass-794';
        await visitor.getByLabel(/^New password/).fill(password);
        await visitor.getByLabel(/^Confirm new password/).fill(password);
        await visitor.getByRole('button', { name: 'Activate account' }).click();
        await expect(visitor.getByRole('status')).toContainText('Account updated');
        await visitor.getByRole('link', { name: 'Member login', exact: true }).click();
        await visitor.getByLabel('Registration number or verified email').fill('MEMBER-E2E-001');
        await visitor.getByLabel(/^Password/).fill(password);
        await visitor.getByRole('button', { name: 'Sign in', exact: true }).click();
        await expect(visitor.getByRole('heading', { name: 'Your membership', exact: true })).toBeVisible();
        await visitor.getByRole('link', { name: 'Profile', exact: true }).click();
        await expect(visitor.getByText('MEMBER-E2E-001', { exact: true })).toBeVisible();
        await visitor.getByLabel('Biography').fill('Learning diplomacy with our university community.');
        await visitor.getByRole('button', { name: 'Save profile' }).click();
        await expect(visitor.getByRole('status')).toContainText('Profile saved');
        await visitor.getByLabel('Profile photo (PNG or JPEG, up to 2 MiB)').setInputFiles(process.env.MUNC_E2E_PHOTO);
        await expect(visitor.getByAltText('Your profile')).toBeVisible();
        for (const width of [1440, 768, 375]) {
            await visitor.setViewportSize({ width, height: 1000 });
            expect(await visitor.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width+1);
            await visitor.evaluate(() => window.scrollTo(0, 0));
            await visitor.screenshot({ path: testInfo.outputPath(`membership-${width}.png`), fullPage: true });
        }
        await admin.getByRole('button', { name: 'Close dialog', exact: true }).click();
        await admin.reload();
        await admin.getByRole('button', { name: 'Manage', exact: true }).click();
        await admin.getByLabel('Identity evidence / decision reason').fill('Officer-reviewed temporary suspension for isolated test.');
        await admin.getByRole('button', { name: 'Suspend', exact: true }).click();
        await visitor.reload();
        await expect(visitor).toHaveURL(/\/member\/login$/);
        await admin.getByRole('button', { name: 'Restore membership', exact: true }).click();
        await expect(admin.getByRole('dialog').getByText('active', { exact: true })).toBeVisible();
    } finally {
        await adminContext.close();
        await memberContext.close();
    }
});
