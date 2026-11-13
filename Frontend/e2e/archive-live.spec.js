import { existsSync } from 'node:fs';
import { test, expect } from '@playwright/test';
import { events } from '../src/data/events.js';
import { eventDescriptions } from '../src/data/eventDescriptions.js';

test('every historical URL, editorial description, gallery and image path survives API downtime', async ({ page }) => {
    test.setTimeout(90000);
    const assets = new Set(events.flatMap(event => [event.coverImage, event.cardDesktop, event.cardMobile, ...event.gallery]).filter(Boolean));
    for (const asset of assets) expect(existsSync(new URL(`../public${asset}`, import.meta.url)), asset).toBe(true);
    await page.route('**/api/**', route => route.abort('failed'));
    await page.goto('/events');
    await expect(page.getByText(/Current events are temporarily unavailable/)).toBeVisible();
    await expect(page.getByRole('link', { name: /^View details:/ })).toHaveCount(events.length);
    for (const event of events) {
        await page.goto(`/events/${event.slug}`, { waitUntil: 'domcontentloaded' });
        await expect(page.getByRole('heading', { name: event.title, exact: true })).toBeVisible();
        await expect(page.getByText(eventDescriptions[event.id] || event.fullDescription, { exact: true })).toBeVisible();
        await expect(page.getByRole('button', { name: /^Open gallery image/ })).toHaveCount(event.gallery.length);
        expect(await page.locator('.event-story-figure img').getAttribute('src')).toBe(event.coverImage || event.cardDesktop);
    }
    const galleryEvent = events.find(event => event.gallery.length > 1);
    await page.goto(`/events/${galleryEvent.slug}`);
    await page.getByRole('button', { name: 'Open gallery image 1', exact: true }).click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await page.keyboard.press('ArrowRight');
    await expect(page.getByRole('dialog').getByRole('img')).toHaveAttribute('src', galleryEvent.gallery[1]);
    await page.keyboard.press('Escape');
    await expect(page.getByRole('dialog')).toHaveCount(0);
    await page.goto('/events/not-a-real-event');
    await expect(page.getByRole('heading', { name: 'Event details unavailable', exact: true })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Back to all events' })).toBeVisible();
});
