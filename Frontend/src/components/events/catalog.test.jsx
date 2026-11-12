import { beforeEach, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { events } from '../../data/events';
import { api } from '../../services/api';
import { backendEvent, dhakaDate, mergeEventCatalog } from '../../services/eventCatalog';
import EventsPage from '../../pages/EventsPage';
vi.mock('../../services/api', () => ({ api: { publicList: vi.fn() } }));
const remote = { id: 9, slug: 'national-mun-2027', title: 'National MUN 2027', status: 'published', event_type: 'Conference', start_date: '2027-01-01T20:00:00Z', end_date: null, description: 'Current event', registration_open: true, cover_image: 'https://example.invalid/cover.png' };
beforeEach(() => { api.publicList.mockReset(); });

it('combines published events with immutable historical records and Dhaka dates', () => {
    const before = JSON.stringify(events);
    const merged = mergeEventCatalog(events, [remote, { ...remote, slug: 'draft', status: 'draft' }]);
    expect(merged).toHaveLength(events.length + 1);
    expect(merged[0].slug).toBe('national-mun-2027');
    expect(dhakaDate(remote.start_date)).toBe('2027-01-02');
    expect(merged[0].registrationSlug).toBe(remote.slug);
    expect(JSON.stringify(events)).toBe(before);
});

it('deduplicates by slug or exact title/date while preserving archive content and URLs', () => {
    const historical = [{ ...events[0], title: 'Historical title', date: '2027-01-02', year: 2027 }];
    const sameSlug = { ...remote, slug: historical[0].slug, title: 'Do not replace editorial content' };
    const sameIdentity = { ...remote, title: ' Historical   title ', slug: 'alternate-api-slug' };
    const merged = mergeEventCatalog(historical, [sameSlug, sameIdentity, remote, remote]);
    expect(merged).toHaveLength(2);
    const retained = merged.find(item => item.slug === historical[0].slug);
    expect(retained.coverImage).toBe(historical[0].coverImage);
    expect(retained.gallery).toEqual(historical[0].gallery);
    expect(retained.title).toBe('Historical title');
    expect(historical[0].registrationSlug).toBeUndefined();
    expect(backendEvent({ ...remote, cover_image: 'javascript:alert(1)' }).coverImage).toBe('');
    expect(backendEvent({ ...remote, start_date: null })).toBeNull();
});

it('keeps the full archive usable while the API loads or fails', async () => {
    api.publicList.mockRejectedValue({ status: 503 });
    render(<MemoryRouter><EventsPage /></MemoryRouter>);
    expect(screen.getByRole('heading', { name: 'Events Archive' })).toBeVisible();
    expect(screen.getAllByRole('link', { name: /^View details:/ })).toHaveLength(events.length);
    expect(await screen.findByText(/Current events are temporarily unavailable/)).toBeVisible();
    expect(screen.getAllByRole('link', { name: /^View details:/ })).toHaveLength(events.length);
    expect(screen.getByRole('button', { name: 'Retry current events' })).toBeVisible();
});

it('shows registration links only for API events with an open published form', async () => {
    api.publicList.mockResolvedValue([remote, { ...remote, id: 10, title: 'Closed conference', slug: 'closed-conference', registration_open: false }]);
    render(<MemoryRouter><EventsPage /></MemoryRouter>);
    expect(await screen.findByRole('link', { name: 'Register for National MUN 2027' })).toHaveAttribute('href', '/events/national-mun-2027/register');
    expect(screen.queryByRole('link', { name: 'Register for Closed conference' })).not.toBeInTheDocument();
});
